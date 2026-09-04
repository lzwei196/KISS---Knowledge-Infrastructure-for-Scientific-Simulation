# Issue: Make KI Harness Planning a Mandatory Application Gate

## Priority and Scope

- Severity: High
- Priority: P0/P1
- Components: GeoForge Server, GeoForge Desktop, KI Harness, project runtime, provider adapters
- Providers affected: Claude Code, OpenAI Codex, Kimi Code, DeepSeek API, and future providers

## Summary

GeoForge Desktop currently injects the KI Harness into the agent context correctly. However, most Harness constraints are still **soft prompt instructions**, not application-enforced gates.

The application does not currently require an agent to:

1. Resolve every KI involved in the requested workflow;
2. Inspect the KI packages, software, data, and project environment before execution;
3. Produce a structured plan and data inventory;
4. Discuss important scientific choices with the user;
5. Obtain approval before downloading data, writing scientific inputs, compiling software, or running models;
6. Prove completion with real files, acquisition receipts, execution receipts, and validation evidence.

As a result, an agent can receive the correct Harness instructions but still skip planning, create substitute scripts, improvise missing model components, or run an incomplete workflow. The user may then see a plausible explanation or plot even though the requested KI workflow was never fully executed or validated.

This is provider-independent and cannot be solved reliably by making the prompt longer. GeoForge Server and Desktop need a shared orchestration state machine with machine-enforced planning, approval, execution, and evidence gates.

---

## Current Behavior: The Harness Is Loaded but Not Gated

The shared Harness already supports two modes:

- `execute=False`: inspect-only planning mode; the agent may read but must not execute;
- `execute=True`: execution mode; the agent may operate the KI according to its validated protocol.

Relevant implementations:

- `ki_tools_common/ki_tools_common/harness/ki_harness.py`
- `kiss/kiss_cli/prompt.py`

The current Desktop chat path nevertheless enters execution mode immediately:

- `prompt.compose(..., execute=True)` is the default behavior;
- `compose_multi(...)` currently hard-codes `execute=True`;
- Project progress can be advanced through agent-reported status;
- No `plan.json`, `data-inventory.json`, or user approval receipt is required;
- The tool layer does not block downloads, file writes, compilation, or model execution before approval.

The effective flow is therefore:

```text
User describes a scientific task
            ↓
GeoForge injects the KI Harness in execution mode
            ↓
The agent decides whether planning is necessary
            ↓
The agent may immediately download, write, compile, or run
```

The required flow is:

```text
User describes a scientific task
            ↓
Resolve every required KI
            ↓
Planning Gate (Harness execute=False)
  - Read KI protocols, diagnostics, software state, and existing data
  - Do not download, write scientific inputs, compile, or run
  - Produce a plan and data inventory
            ↓
GeoForge validates the planning artifacts
            ↓
Ask the user only for material scientific decisions
            ↓
User approval
            ↓
Execution Gate (Harness execute=True)
  - Execute only the approved plan
  - Record data, tool, model, and output evidence
            ↓
Evidence and Result Gate
  - Validate files, executions, and scientific sanity
            ↓
Deliver verified results
```

---

## Reproduction: VIC–CaMa-Flood Project

A user requested a coupled VIC–CaMa-Flood flood simulation.

### What happened

1. The Kimi session did contain `[KI HARNESS v1]` and `[GEOFORGE HARNESS RECEIPT]`;
2. The project bound only `VIC`; it did not bind `CaMa_Flood`;
3. The Harness was injected in execution mode without a separate planning phase;
4. Without a CaMa-Flood KI, the agent wrote its own CaMa map and configuration preparation logic;
5. The NASA POWER data were genuinely downloaded and transformed, but complete raw acquisition receipts were not preserved and the file placement confused the UI status;
6. A real CaMa binary was executed, but it used handmade, unverified river maps and parameters;
7. The outlet-discharge output contained no positive values and was not a valid coupled VIC–CaMa scientific result;
8. The project UI still advanced into running/results and displayed a plot.

### Conclusion from the reproduction

- Successful Harness injection does not prove application-level enforcement;
- Binding only one KI is insufficient for a coupled natural-language request;
- Agent-reported progress is not scientific evidence;
- A process exiting successfully does not prove a valid model run;
- A generated plot does not prove that the requested workflow passed validation.

---

## Root Causes

### 1. No enforceable planning state

The project UI has stages such as understanding, software, preparing, validating, running, and results. These are presentation states, not permission boundaries. There is no planning state that restricts the agent to read-only inspection.

### 2. Planning and execution share the same agent context

The initial provider turn receives an execution contract. The agent does not need to pass a verifiable checkpoint before execution tools become available.

### 3. Multi-KI resolution is not a pre-execution gate

When the user says “VIC–CaMa,” the session may still bind only VIC. The agent can then treat CaMa as a generic external component and improvise it instead of loading the second KI.

### 4. Agent self-report can advance project status

`report_project_progress` is useful for UI updates, but it cannot serve as completion evidence. GeoForge does not consistently verify that the files, downloads, processes, and scientific checks corresponding to a reported stage actually exist.

### 5. Data and execution provenance are optional

There is no universal requirement that every acquisition produces a machine-readable receipt or that every model execution produces a standard run receipt.

### 6. The Harness is not a tool authorization policy

The prompt tells the agent not to reimplement scientific logic or bypass KI tools, but providers can still violate prompt instructions. GeoForge must enforce these restrictions at the orchestration and tool-proxy layers.

---

## Required Shared State Machine

GeoForge Server and Desktop should share the following project states:

```text
NEW
  → RESOLVING_KIS
  → PLANNING
  → PLAN_REVIEW
  → WAITING_FOR_USER (only when a material choice exists)
  → APPROVED
  → EXECUTING
  → VERIFYING
  → COMPLETED

Any applicable state may transition to:
  → BLOCKED
  → FAILED
  → REPLAN_REQUIRED
```

### State permissions

| State | Allowed | Forbidden |
|---|---|---|
| `RESOLVING_KIS` | Search the KI library and read metadata | Download, write scientific inputs, run models |
| `PLANNING` | Read KI protocols, DAGs, diagnostics, project files, and software state | Download, compile, modify scientific inputs, run models |
| `PLAN_REVIEW` | Validate and display planning artifacts | Execute the plan |
| `WAITING_FOR_USER` | Receive a decision, file, login, licence, or permission | Silently assume the user's choice |
| `APPROVED` | Create an immutable approval receipt | Modify the approved plan without invalidating approval |
| `EXECUTING` | Run tools and models declared in the approved plan | Introduce unselected models or substitute scientific algorithms |
| `VERIFYING` | Inspect outputs and run KI validation checks | Mark failed results as complete |
| `COMPLETED` | Present verified results and evidence | Modify sealed run evidence |

---

## Mandatory Planning Artifacts

### 1. `runs/plan.json`

Suggested minimum structure:

```json
{
  "schema_version": "1.0",
  "goal": "Run a coupled VIC–CaMa-Flood flood simulation",
  "selected_kis": ["VIC", "CaMa_Flood"],
  "steps": [
    {
      "id": "prepare_vic_forcing",
      "ki": "VIC",
      "tool": "tools/...",
      "inputs": ["forcing", "soil", "vegetation"],
      "outputs": ["vic_runoff"],
      "status": "planned"
    },
    {
      "id": "route_with_cama",
      "ki": "CaMa_Flood",
      "inputs": ["vic_runoff", "river_map"],
      "outputs": ["routed_discharge", "flood_depth"],
      "status": "planned"
    }
  ],
  "scientific_choices": [],
  "unresolved_questions": [],
  "created_at": "ISO-8601 timestamp"
}
```

### 2. `runs/data-inventory.json`

```json
{
  "schema_version": "1.0",
  "items": [
    {
      "id": "meteorological_forcing",
      "required_by": ["VIC"],
      "status": "missing",
      "acceptable_sources": ["CMFD", "NASA POWER"],
      "chosen_source": null,
      "local_paths": [],
      "agent_resolvable": true,
      "needs_user": false
    },
    {
      "id": "cama_river_map",
      "required_by": ["CaMa_Flood"],
      "status": "missing",
      "acceptable_sources": ["validated CaMa map package"],
      "chosen_source": null,
      "local_paths": [],
      "agent_resolvable": false,
      "needs_user": true
    }
  ]
}
```

### 3. `runs/approval.json`

GeoForge UI or Server must create this receipt. The agent must not approve its own plan.

```json
{
  "schema_version": "1.0",
  "plan_sha256": "...",
  "data_inventory_sha256": "...",
  "approved_by": "user",
  "approved_at": "ISO-8601 timestamp",
  "decisions": {
    "forcing_source": "NASA_POWER"
  }
}
```

If `plan.json` or `data-inventory.json` changes after approval, the approval must become invalid and the project must transition to `REPLAN_REQUIRED`.

---

## Execution Gate Rules

GeoForge must not expose execution-capable tools until all of the following are true:

1. At least one KI is selected;
2. Every primary model named or implied by the request is resolved to a KI or explicitly recorded as unsupported;
3. Every selected KI has a valid Harness receipt;
4. `plan.json` passes schema and reference validation;
5. `data-inventory.json` is complete;
6. All required user decisions are resolved;
7. `approval.json` matches the current plan and inventory hashes.

When execution begins, GeoForge should start a new provider turn or session and inject:

- The KI Harness in `execute=True` mode;
- The approved plan;
- Approved data sources and paths;
- The exact selected-KI set;
- Tool-policy restrictions that prevent unapproved deviations;
- Harness receipts and fingerprints.

The project must transition to `REPLAN_REQUIRED` if the agent attempts to:

- Add an unselected model;
- Create a substitute model or scientific core algorithm;
- Change the data source;
- Change the study region, period, scenario, calibration objective, or other material scientific decision.

---

## Data Acquisition Receipts

Every real download should create `runs/data-receipts/<item-id>.json` containing at least:

```json
{
  "source": "NASA POWER",
  "request_url": "https://...",
  "requested_at": "ISO-8601 timestamp",
  "http_status": 200,
  "raw_files": [
    {"path": "inputs/raw/...json", "sha256": "...", "bytes": 12345}
  ],
  "processed_files": [
    {"path": "inputs/forcing/...", "sha256": "...", "bytes": 67890}
  ],
  "transform_tool": "absolute KI tool path",
  "units_before": {},
  "units_after": {}
}
```

The UI may display “Downloaded” or “Ready” only when both the receipt and referenced files exist. An agent message alone must not change the data status.

The UI should distinguish public downloads, user-provided data, generated or transformed data, bundled validation examples, and synthetic or experimental data.

---

## Model Execution and Result Receipts

Every model execution should produce `runs/model-runs/<run-id>.json`:

```json
{
  "ki": "CaMa_Flood",
  "executable": "/absolute/path/to/model",
  "executable_sha256": "...",
  "command": ["..."],
  "cwd": "...",
  "started_at": "...",
  "finished_at": "...",
  "exit_code": 0,
  "stdout_log": "runs/logs/...",
  "stderr_log": "runs/logs/...",
  "inputs": [{"path": "...", "sha256": "..."}],
  "outputs": [{"path": "...", "sha256": "..."}],
  "validation": {
    "status": "passed|failed|warning",
    "checks": []
  }
}
```

`exit_code == 0` proves only that the process exited. It does not prove a scientifically valid run. Completion must additionally require the KI's output checks, such as:

- Numeric range and sign checks;
- NaN/Inf checks;
- Mass, energy, or water balance;
- Timeline completeness;
- Presence of physically necessary variability;
- Agreement with observations or validation-case thresholds when applicable.

---

## Multi-KI Resolution

During planning, GeoForge must resolve model entities in the user request.

Example request:

```text
Run a VIC–CaMa flood simulation.
```

Expected resolution:

```json
{
  "selected_kis": ["VIC", "CaMa_Flood"],
  "coupling": [
    {"from": "VIC.runoff", "to": "CaMa_Flood.runoff_forcing"}
  ]
}
```

If `CaMa_Flood` is unavailable, planning must explain that:

- Only VIC is currently available;
- VIC can produce a CaMa-compatible runoff input, but it cannot replace the CaMa KI;
- GeoForge cannot create an unverified river map and call the result a valid coupled simulation;
- The supported choices are to install/load the CaMa KI, provide validated data, or reduce the task to VIC only.

---

## Shared Server/Desktop Contract

The state machine, JSON schemas, and gate decisions should be a versioned shared protocol or library. Server and Desktop should not duplicate prompt wording and infer completion differently.

Suggested Server API semantics:

```text
POST /projects/{id}/resolve-kis
POST /projects/{id}/plan
GET  /projects/{id}/plan
POST /projects/{id}/approve
POST /projects/{id}/execute
GET  /projects/{id}/events
GET  /projects/{id}/evidence
```

Required constraints:

- `/execute` validates the approval hash on the server;
- Changing a UI field cannot bypass the gate;
- Server and Desktop use the same schema version;
- Provider adapters handle communication but do not decide whether execution is permitted;
- The agent cannot approve its own plan or certify its own results.

---

## User Experience

The user should not need to read a complete KI DAG or internal checklist. The planning UI should summarize only what matters:

```text
What I understand
  VIC + CaMa-Flood flood simulation at Bengbu, Huai River

GeoForge can handle
  ✓ Check both model installations
  ✓ Prepare VIC inputs
  ✓ Convert VIC runoff for CaMa

Still missing
  ! Validated CaMa river map
  ! Bengbu observations (only required for quantitative calibration)

One decision for you
  Choose forcing: CMFD / NASA POWER quick trial

                     [Edit plan] [Approve and start]
```

Technical paths, schemas, tools, and KI requirements can remain available in an expandable details panel.

---

## Harness Receipts and Context Continuity

Every provider phase should record:

```json
{
  "harness_marker": "KI HARNESS v1",
  "harness_mode": "plan|execute",
  "harness_sha256": "...",
  "ki_name": "VIC",
  "ki_root": "...",
  "skill_sha256": "...",
  "provider": "Kimi Code",
  "session_id": "...",
  "injected_at": "..."
}
```

After provider context compaction, GeoForge should re-inject a compact Harness contract and approved-plan summary. This improves long-turn reliability but does not replace the application gate.

---

## Acceptance Criteria

### A. Mandatory planning

- [ ] Every new scientific project starts with `execute=False`;
- [ ] Planning cannot call download, write, compile, or model-execution tools;
- [ ] Execution cannot begin without valid `plan.json` and `data-inventory.json`;
- [ ] GeoForge may auto-approve a low-risk plan when there is no material user decision;
- [ ] Data-source, licence, login, private-file, permission, and high-impact scientific decisions require user input.

### B. Multi-KI workflows

- [ ] “VIC–CaMa” binds both `VIC` and `CaMa_Flood`;
- [ ] If either KI is missing, GeoForge does not claim the coupled run is complete;
- [ ] Adding another model after approval triggers replanning.

### C. Data authenticity

- [ ] Every downloaded item has a receipt, hashes, raw files, and transformation record;
- [ ] The UI does not show “Ready” when referenced files are absent;
- [ ] Agent text cannot independently change a data item from missing to ready;
- [ ] Public downloads, user data, generated data, and validation examples are visibly distinct.

### D. Model and result authenticity

- [ ] Every model run records command, binary hash, exit code, logs, and outputs;
- [ ] A successful exit with failed scientific checks becomes `FAILED_VALIDATION`, not `COMPLETED`;
- [ ] A handwritten substitute cannot be presented as the KI's scientific core;
- [ ] Results created from unverified inputs are clearly marked experimental/unverified.

### E. Provider consistency

The same suite must pass with:

- [ ] Claude Code
- [ ] OpenAI Codex
- [ ] Kimi Code
- [ ] DeepSeek API

All providers must pass through the same application gates, regardless of how reliably they follow prompt instructions.

---

## Minimum Regression Tests

### Test 1: Single KI with complete data

Run a small validated DSSAT example.

Expected: automatic plan → no material decision → approval → execution → evidence validation → completion.

### Test 2: Coupled workflow with a missing KI

Request VIC–CaMa while only VIC is loaded.

Expected: planning detects the missing `CaMa_Flood` KI, blocks improvised CaMa logic, and waits for installation/loading or task reduction.

### Test 3: User must select a data source

CMFD is unavailable, while NASA POWER can support a lower-resolution trial.

Expected: the planning UI explains the trade-off; download begins only after approval; a complete acquisition receipt is produced.

### Test 4: Agent attempts to bypass planning

Instruction: “Run it directly and do not ask me.”

Expected: the tool proxy rejects execution until planning and approval are complete.

### Test 5: Scientifically invalid output

The model exits with code 0, but outputs are all zero, invalidly signed, or otherwise fail KI checks.

Expected: result validation fails and the project does not display scientific completion.

### Test 6: Approved plan changes

After approval, change the forcing, model, period, scenario, or region.

Expected: approval becomes invalid and the project enters `REPLAN_REQUIRED`.

---

## Non-Goals

- Do not require the user to understand the complete DAG or every KI file;
- Do not require manual approval for every low-risk step;
- Do not replace natural-language planning with a rigid form-only workflow;
- Do not prohibit exploratory analysis, but distinguish it from verified model execution;
- Do not treat a longer prompt as the primary solution.

---

## Suggested Implementation Order

1. Define the shared state machine and JSON schemas;
2. Switch the first Desktop/Server agent phase to `execute=False`;
3. Add plan and data-inventory validators;
4. Add immutable approval receipts and hashes;
5. Enforce state permissions in the tool proxy;
6. Add multi-KI resolution and coupling checks;
7. Add acquisition and model-run receipts;
8. Add the scientific evidence gate;
9. Align Server and Desktop on the versioned protocol;
10. Run the shared regression suite across all four providers.

## Definition of Done

For every new scientific simulation task, no provider can begin scientific execution without a machine-validated plan and any required user approval. When GeoForge displays “Completed,” it must be able to prove—through local or server-side machine-readable evidence—which KIs, data, programs, commands, outputs, and validation checks were used and passed.
