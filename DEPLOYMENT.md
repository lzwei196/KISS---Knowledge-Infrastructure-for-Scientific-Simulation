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
- Tends to give up and report literature values instead of debugging tool failures
- Weaker at Fortran/fixed-width format handling — needs explicit tool references

### Qwen Code
- Convention unclear — `QWEN.md` in project root (assumed)
- Alibaba Cloud authentication
- Needs testing for instruction file loading reliability

---

*This document is part of KDT v4.0. Last updated: 2026-04-01.*
*Lessons derived from deploying HydroCraft (31 models, 5 providers) at app.hydrocraft.ai.*
