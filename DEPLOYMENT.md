# KDT Deployment Guide: Serving KI Through Multiple Agent Providers

**Read this BEFORE deploying a KI-powered service to end users.** These issues only surface in production — they are invisible during single-agent development and testing.

> This document captures lessons learned from deploying HydroCraft (31 models, ~436 tools) as a multi-provider web service at [app.hydrocraft.ai](https://app.hydrocraft.ai).

---

## The Core Problem

During development, you test with one agent (e.g., Claude Code) that auto-loads your project instructions (`CLAUDE.md`). Everything works. Then you deploy a web service with multiple agent providers (Claude, Codex, Gemini, Kimi, Qwen) and discover:

1. **Each provider has a different instruction file convention** — there is no standard
2. **Agents without project instructions fail silently** — they run models with wrong units, skip validated tools, and produce scientifically incorrect results with no error message
3. **The agent thinks it succeeded** — it reports "simulation complete" when the output is garbage
4. **Users cannot tell** — they see a polished response with tables and plots, not knowing the underlying model was misconfigured

This is the **deployment gap**: KI works perfectly when the agent reads it, and fails catastrophically when it doesn't.

---

## Rule 1: Every Provider Must Read the Same Instructions

### The Provider Instruction File Map

Each AI coding agent CLI has its own convention for project-level instructions:

| Provider | Instruction File | Auto-loaded? | Convention |
|----------|-----------------|-------------|------------|
| **Claude Code** | `CLAUDE.md` in project root | Yes | Anthropic standard |
| **OpenAI Codex** | `AGENTS.md` in project root | Yes | OpenAI standard |
| **Gemini CLI** | `~/.gemini/GEMINI.md` (global) | Yes | Google convention |
| **Kimi Code** | `.kimi/skills/<name>/SKILL.md` | Yes (as skill) | Moonshot skill system |
| **Qwen Code** | `QWEN.md` in project root | Likely | Alibaba convention |
| **Cursor** | `.cursorrules` in project root | Yes | Cursor convention |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Yes | GitHub convention |

### The Fix: Symlink All to One Source of Truth

Maintain ONE canonical instruction file and symlink all others to it:

```bash
# Source of truth
CLAUDE.md                    # 1054 lines, comprehensive

# Symlinks (auto-sync with source)
AGENTS.md    -> CLAUDE.md    # Codex reads this
QWEN.md      -> CLAUDE.md    # Qwen reads this
~/.gemini/GEMINI.md -> /path/to/CLAUDE.md  # Gemini reads this

# Copy (for providers that use skill systems with different frontmatter)
.agents/skills/hydrocraft/SKILL.md  # Kimi + Codex skills (copied, not symlinked)
```

**Why a copy for Kimi?** Kimi's skill system requires YAML frontmatter (`name:`, `description:`) at the top of SKILL.md. The canonical `CLAUDE.md` doesn't have this. So we copy the full content and add the frontmatter. This means Kimi's version can drift — document a sync procedure.

### Sync Procedure

When the canonical instruction file is updated:

```bash
# Symlinks auto-sync (no action needed)
# For copies (Kimi skill), manually re-copy:
cp CLAUDE.md .agents/skills/hydrocraft/SKILL.md
# Re-add YAML frontmatter if needed
```

---

## Rule 2: The System Prompt Must Include Model-Specific Guardrails

Even when an agent reads the full instruction file, the **system prompt injected by the web backend** is often more influential for non-Claude providers because:

- Some CLIs truncate long instruction files
- Some CLIs prioritize the initial prompt over project files
- The instruction file tells the agent to "read CLAUDE.md" but the agent may not actually do it

### What Must Be in the System Prompt

For non-auto-loading providers, the system prompt injected at conversation start must include at minimum:

```
⚠️ MODEL-SPECIFIC GUARDRAILS (silent errors if violated):

1. EVERY model has a Knowledge Infrastructure at models/<ModelName>/knowledge_infrastructure/SKILL.md
   YOU MUST read the SKILL.md BEFORE running ANY model.

2. NEVER write custom scripts when a validated tool exists.
   Check models/<Model>/knowledge_infrastructure/tools/ first.

3. Model-specific unit traps (the model will NOT warn you):
   - DSSAT: Use dssat_workdir_setup.py, NEVER manually edit FileX
   - GLM:   Rain in m/day NOT mm/day (÷1000)
   - ParFlow: K in m/hr NOT m/day (÷24)
   - WRF-Hydro: RAINRATE in mm/s NOT mm/3hr (÷10800)
   - MODFLOW: FloPy precision='double' for reading .hds
   - NASA POWER: Precip ÷24, Radiation ×277.78
```

### The DSSAT Trap (Case Study)

This is the most instructive example because it produces **believable wrong results**.

**What happened:** Kimi Code was asked to run a DSSAT crop simulation for Montreal. It:
1. ✅ Correctly identified the location, fetched NASA POWER weather
2. ✅ Found appropriate Canadian cultivars (MANITOU wheat, ALTONA soy)
3. ❌ Tried to manually edit DSSAT FileX files instead of using `dssat_workdir_setup.py`
4. ❌ Hit Fortran fixed-width column alignment errors (soybean, wheat failed)
5. ❌ Weather station reference stayed as Florida (UFGA) instead of Montreal (MTRL)
6. ❌ Reported "expected yields from literature" as if they were simulation results

**Why it happened:** Kimi's system prompt didn't include the rule "ALWAYS use `dssat_workdir_setup.py`". The `dssat_workdir_setup.py` utility exists precisely because DSSAT's FileX format has 6+ known pitfalls that are impossible to handle with simple text replacement.

**The lesson:** Model-specific validated tools exist because someone already hit every possible error. If an agent doesn't know they exist, it will re-discover each error the hard way — or worse, produce wrong results without discovering the error at all.

---

## Rule 3: The Skill Name Collision Problem

### The Problem

KDT uses `SKILL.md` as the standard filename for model operational documentation:
```
models/VIC/knowledge_infrastructure/SKILL.md
models/DSSAT/knowledge_infrastructure/SKILL.md
models/GLM/knowledge_infrastructure/SKILL.md
... (31 files, all named SKILL.md)
```

Some agent providers also use `SKILL.md` as their skill definition format:
```
.kimi/skills/hydrocraft/SKILL.md      # Kimi's project skill
.kimi/skills/other-skill/SKILL.md     # Another Kimi skill
.codex/skills/hydrocraft/SKILL.md     # Codex's project skill
```

### Why It Doesn't Conflict (Currently)

Agent skill discovery is scoped:
- **Kimi** only scans `.kimi/skills/` (not the entire project tree)
- **Codex** only scans `.codex/skills/` (not the entire project tree)
- **Model SKILL.md files** at `models/*/knowledge_infrastructure/` are NOT auto-discovered

The agent reads model SKILL.md files only when explicitly instructed: "Read `models/GLM/knowledge_infrastructure/SKILL.md` before running GLM."

### When It Will Conflict

If a future agent provider implements **recursive skill discovery** (scanning the entire project for `SKILL.md` files), it would find 31+ model SKILLs and try to load them all as separate skills. This would:
- Consume the entire context window with irrelevant model documentation
- Confuse the agent about which "skill" to apply
- Potentially override the project-level SKILL.md

### Mitigation

1. **Monitor new provider conventions** — check if they do recursive discovery before deploying
2. **Consider renaming model docs** — e.g., `OPERATIONS.md` or `MODEL_GUIDE.md` instead of `SKILL.md` to avoid future collisions
3. **Use `.gitignore`-style exclusion** if the provider supports it (e.g., `.kimiignore`)

---

## Rule 4: Non-Claude Agents Need Explicit "Read First" Instructions

Claude Code automatically reads `CLAUDE.md` before every response. Other providers may read their instruction file once at session start but not re-read it. This means:

### What Works for Claude But Fails for Others

| Instruction | Claude Code | Other Providers |
|------------|-------------|-----------------|
| "Read CLAUDE.md first" | Already loaded | May or may not do it |
| "Check models/X/SKILL.md before running X" | Reliable | Unreliable — may skip |
| "Use dssat_workdir_setup.py" | Follows it | May write custom code instead |
| "Check units in SKILL.md" | Follows it | May guess units from variable names |

### The Fix: Repeat Critical Rules in Multiple Places

For non-Claude providers, critical rules must appear in:
1. **The instruction file** (AGENTS.md, SKILL.md, etc.)
2. **The system prompt** (injected by backend at conversation start)
3. **The follow-up prompt** (injected with each subsequent message)

The follow-up prompt is the most reliable because it's always present in context:

```python
# In the web backend, inject with every message for non-Claude providers:
reminder = """
[REMINDER — MANDATORY RULES]
1. Read the model's SKILL.md at models/<Name>/knowledge_infrastructure/ BEFORE running it
2. Use validated tools from the KI — NEVER write custom scripts
3. Check unit conversion tables — models do NOT warn about wrong units
"""
effective_message = reminder + user_message
```

---

## Rule 5: Concurrency Is Not Free

### Single-Agent Development vs Multi-User Service

| Aspect | Development | Production |
|--------|-------------|------------|
| Users | 1 (you) | Multiple simultaneous |
| Agent processes | 1 | N (one per conversation) |
| Model processes | 1 | N (VIC, CaMa, DSSAT competing for CPU/RAM) |
| Memory | Predictable | Unbounded (each agent + model allocates independently) |
| Failure mode | You see the error | Users see "no response" or crash |

### What Goes Wrong

1. **Memory exhaustion**: Each CLI agent subprocess uses 200-500 MB. Each model run uses 500 MB - 4 GB. With 3 concurrent users running VIC + CaMa-Flood, you need 6-15 GB free.
2. **CPU contention**: VIC is single-threaded but CPU-bound. Multiple VIC runs on a 96-core machine are fine. Multiple MSWX forcing extractions (disk I/O bound) will serialize on HDD.
3. **Swap death**: When RAM fills, Linux starts swapping. Model runtimes go from minutes to hours. The user thinks it's stuck. They refresh the page. A new agent spawns. The old one keeps running. Now you have 2x the load.
4. **WebSocket timeout**: Cloudflare kills idle WebSocket connections after ~30-60 seconds. During long model runs with no output, the connection drops. The simulation continues but the user loses the response.

### Mitigations

1. **Set `MAX_CONCURRENT_JOBS`** in the backend to limit parallel model runs
2. **Implement WebSocket keepalive pings** (every 20 seconds) to prevent Cloudflare timeout
3. **Monitor swap usage** — restart backend if swap exceeds 80%
4. **Tell users** in the guide: "This is a demo, not a production service. Coordinate with other testers."

---

## Rule 6: Silent Errors Are Worse in Production

In development, you check results carefully. In production, the user trusts the agent's output.

### The Silent Error Amplification Chain

```
Development:  wrong unit → wrong result → you notice → you fix it
Production:   wrong unit → wrong result → agent says "simulation complete!" 
              → user downloads CSV → publishes paper with wrong numbers
```

### Defense: Preflight Validators Must Run Automatically

The `preflight_forcing.py` validator catches unit mismatches BEFORE the model runs. In production:

1. **Make it mandatory** — the system prompt should say "run preflight check before every model execution"
2. **Fail loud** — if preflight fails, the agent must tell the user, not silently proceed
3. **Log it** — record all preflight results for audit

---

## Checklist: Before Deploying a KI Service

- [ ] All provider instruction files created (symlinked to canonical source)
- [ ] System prompt includes model-specific guardrails for non-auto-loading providers
- [ ] Follow-up prompt reminder injected with every message for non-Claude providers
- [ ] WebSocket keepalive implemented (ping every 20s for Cloudflare)
- [ ] Concurrent job limit set in backend config
- [ ] Preflight validators integrated into agent workflow
- [ ] User guide documents: server specs, single-user limitation, expected runtimes
- [ ] Test each provider independently: can it find and read the instruction file?
- [ ] Test each provider with a model that has known unit traps (DSSAT is ideal)
- [ ] Monitor swap usage and set up alerting

---

## Provider-Specific Notes

### Claude Code
- Reads `CLAUDE.md` automatically, reliably
- Best KI integration — follows complex multi-step instructions
- Supports `--resume` for conversation continuity
- Memory system (`.claude/`) persists learnings across sessions

### OpenAI Codex
- Reads `AGENTS.md` from project root
- Tends to write custom code rather than using existing tools (needs strong guardrails)
- `--full-auto` mode skips confirmation — dangerous for destructive operations

### Gemini CLI
- Reads `~/.gemini/GEMINI.md` (global, not per-project — limitation)
- Good at reading files when instructed, but may not proactively read SKILL.md
- OAuth-based auth (no API key needed)

### Kimi Code
- Skill-based instruction loading (`.kimi/skills/*/SKILL.md`)
- SKILL.md naming collision risk with model KI files (see Rule 3)
- **Requires significantly stronger KI harness than Claude** (see Rule 7 below)
- Observed failure modes across 5 model tests:
  - Writes custom scripts instead of using KI tools (HYPE: 13hr forcing script vs 5min KI tool)
  - Gives up on complex setups ("too complex for demo") instead of executing the pipeline (SWAT+: 3 attempts, 0 completions)
  - Overrides KI tool defaults with wrong values (WRF-Hydro: set CHRTOUT=0, faked discharge)
  - Reports literature values as simulation results when model execution fails (DSSAT: Montreal corn)
  - Manually edits Fortran fixed-width files instead of using validated utilities (DSSAT: FileX)

### Qwen Code
- Convention unclear — `QWEN.md` in project root (assumed)
- Alibaba Cloud authentication
- Needs testing for instruction file loading reliability

---

## Rule 7: Agent-Specific KI Harness Strength

### The Observation

The same KI produces different outcomes depending on which agent reads it. From testing
31 models across 5 providers on HydroCraft:

| Agent | KI Compliance | Harness Needed | Failure Mode |
|-------|--------------|----------------|-------------|
| **Claude Code** | High | Light — CLAUDE.md system prompt is sufficient | Rarely deviates; follows multi-step workflows reliably |
| **OpenAI Codex** | Medium | Medium — needs explicit tool paths in instructions | Tends to write custom code; follows instructions when specific |
| **Gemini CLI** | Medium | Medium — reads files when told but needs reminders | May not proactively read model SKILL.md |
| **Kimi Code** | Low | **Heavy** — needs per-message reminders + anti-shortcut rules | Actively seeks shortcuts; overrides tool defaults; gives up on complex tasks |
| **Qwen Code** | Unknown | Unknown | Insufficient testing data |

### Why Agents Differ

1. **System prompt authority**: Claude Code treats CLAUDE.md as system-level instructions
   (always in context, high priority). Other agents load instruction files with lower priority
   that degrades over long conversations.

2. **Tool usage tendency**: Claude Code defaults to using existing tools and reading documentation.
   Kimi Code defaults to writing new code — even when told not to.

3. **Complexity tolerance**: When a task requires 10+ sequential steps (SWAT+ setup), Claude Code
   executes them methodically. Kimi Code looks for shortcuts after step 2-3.

4. **Failure response**: When a model crashes, Claude Code reads diagnostics and tries the documented
   fix. Kimi Code reports what "should" work from its training data instead.

### Implementing Harness Levels

**Light harness** (Claude Code):
```
Layer 1: CLAUDE.md auto-loaded into system prompt (sufficient)
Layer 2: Minimal reminder about image paths
```

**Medium harness** (Codex, Gemini):
```
Layer 1: AGENTS.md / GEMINI.md loaded at session start
Layer 2: System prompt with model-specific guardrails
Layer 3: Per-message reminder (8 rules)
```

**Heavy harness** (Kimi Code):
```
Layer 1: SKILL.md loaded as project skill
Layer 2: Full system prompt with model-specific guardrails + unit traps
Layer 3: Per-message reminder with 10 rules including:
   - "NO SHORTCUTS — EXECUTE THE FULL PIPELINE"
   - "NEVER skip steps or use 'practical/simplified approach'"
   - "NEVER report literature values as results"
   - "NEVER say 'too complex for this demo'"
   - "If a tool fails, read triplets.yaml — do NOT give up"
   - "USE KI TOOLS — NEVER write custom scripts"
```

### Measuring Harness Effectiveness

Track these metrics per provider to tune harness strength:

| Metric | How to Measure | Target |
|--------|---------------|--------|
| **KI tool usage rate** | Did the agent call KI tools or write custom? | >90% |
| **Pipeline completion rate** | Did the agent finish all steps? | 100% |
| **Shortcut attempts** | Count of "simplified approach" / "too complex" / literature values | 0 |
| **Model execution success** | Did the actual binary produce output? | >80% |
| **Output correctness** | Are values physically reasonable? | >90% |

### Key Insight

> **KI quality is necessary but not sufficient.** The same validated KI that works perfectly
> with Claude Code fails with Kimi Code — not because the KI is wrong, but because the agent
> doesn't follow it. The harness (system prompt + reminders + anti-shortcut rules) is what
> bridges the gap between KI availability and KI compliance.
>
> When deploying a KI service with multiple providers, **test each provider independently**
> and adjust the harness strength until compliance metrics meet targets. Do not assume that
> passing with Claude Code means passing with all providers.

---

*This document is part of KDT v4.0. Last updated: 2026-04-02.*
*Lessons derived from deploying HydroCraft (31 models, 5 providers) at app.hydrocraft.ai.*
