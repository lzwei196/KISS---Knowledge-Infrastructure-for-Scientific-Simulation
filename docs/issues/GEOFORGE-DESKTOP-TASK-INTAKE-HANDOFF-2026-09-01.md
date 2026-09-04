# GeoForge Desktop structural task-intake handoff

Date: 2026-09-01  
Repository: `lzwei196/KISS---Knowledge-Infrastructure-for-Scientific-Simulation`  
Local branch: `mac-version`  
Local base commit at handoff: `9a42d0b`  
Status: implemented and locally built, **not committed or pushed**

This document hands off the current GeoForge Desktop work, with particular focus on the
structural repair to the first scientific chat turn. It also maps the major source files and
runtime artifacts so another developer or Agent can continue without reconstructing the
architecture from scratch.

The earlier planning/approval repair remains relevant and is documented in
[`KI-HARNESS-PLAN-HANDOFF-2026-08-31.md`](KI-HARNESS-PLAN-HANDOFF-2026-08-31.md).
The present document begins one phase earlier: **how a natural-language scientific request
becomes a validated task understanding before planning starts**.

---

## 1. User-visible problem

The user should be able to say:

> 我想要用 CRHM 模拟中国高寒区融雪径流。

The previous Desktop behavior treated the first turn too much like a model selector. In the
reproduced case it answered that the whole phrase was not a model for which it had a KI, then
asked the user to identify the model again. That was not merely a Chinese-tokenization bug.

The architectural order was wrong:

```text
Previous order

user sentence
    -> Desktop regex resolves/queries model names
    -> Desktop creates planning state
    -> Agent receives an already-decided model/planning context
```

The intended order is:

```text
Repaired Auto-KI order

natural-language scientific goal
    -> read-only Agent task-understanding turn
    -> structured intent + proposed KI(s) + material gaps
    -> Desktop validates the handoff
    -> only then: a separate KI planning turn
    -> plan validation and review
    -> approval
    -> setup/execution
    -> evidence validation
```

The Agent is responsible for semantic understanding. The Desktop remains responsible for
state transitions, KI-name validation, permission boundaries, approval and evidence.

---

## 2. Root causes found

### 2.1 Chinese text exposed a lexical defect

`resolve.py` split unknown-model candidates only on whitespace. A string such as
`我想要用CRHM模拟中国高寒区融雪径流` was therefore both:

- correctly matched to `CRHM`; and
- incorrectly treated as one mixed-case unknown model token.

This symptom is fixed by extracting ASCII identifier runs from multilingual text. Real model
separators such as `-`, `_`, `/` and `+` are preserved.

### 2.2 The Desktop performed semantic work before the Agent

`flowrun.pre()` previously allowed the host's regular expressions to resolve, reject or ask
about the model before any Agent had interpreted the scientific goal. A parser can recognize
identifiers, but cannot determine the experiment's area, period, process, scenario, outputs or
scientifically material omissions.

### 2.3 Auto-KI had a contradictory contract

The same initial turn received several incompatible instruction blocks:

- choose and announce a KI;
- read and follow its `SKILL.md`;
- prepare project data and use tools;
- state a scope and possibly ask for approval;
- but, under the flow policy, remain read-only and only choose a model.

Different providers resolved those contradictions differently. The result could look like a
model-name question, premature planning, or a skipped intake.

### 2.4 The API path dropped the strongest intake instruction

The task-intake instruction had initially been appended to an expanded task string, while the
direct API call sent `bare_task`. Therefore DeepSeek/API agents did not actually receive the same
intake contract as a fresh CLI replay. This was a concrete provider-path defect, not a model
quality issue.

### 2.5 CLI selection reporting conflicted with read-only policy

The old design expected native CLIs to report their chosen KI by writing
`runs/project-agent-status.json`, but the intake policy deliberately gives Claude, Codex and Kimi
no project write permission. The architecture now uses a response handoff for CLI providers and
a typed tool for direct APIs.

### 2.6 Choosing a KI was incorrectly treated as planning readiness

A model can be appropriate while the study is still underspecified. The Desktop now distinguishes:

- proposed/validated KI names;
- an intelligible task summary;
- remaining material questions; and
- readiness to create a meaningful plan.

An Agent's `ready_for_planning=true` is evidence, not authority. GeoForge rejects it when the
understanding is empty, `missing` is non-empty, no proposed KI exists, or a user-action request is
still pending.

---

## 3. Implemented behavior

### 3.1 Structured intake contract

The normalized intake object is:

```json
{
  "ready_for_planning": false,
  "understanding": "Use CRHM to study snow accumulation, melt and runoff in a Chinese alpine basin",
  "study_area": "Chinese alpine region; exact basin pending",
  "period": "",
  "process": "snow accumulation, energy-balance melt and runoff generation",
  "scenario": "",
  "requested_outputs": ["snow water equivalent", "snowmelt", "outlet discharge"],
  "missing": ["exact basin or spatial boundary", "simulation period"]
}
```

The initial turn must not download, create scientific inputs, install software, write a plan or
run a model.

### 3.2 Provider-neutral handoff

Direct API providers call the typed `report_project_progress` tool with:

- `selected_kis`; and
- `intake`.

Native CLI providers end their visible response with an invisible HTML comment:

```html
<!-- GEOFORGE_INTAKE {"selected_kis":["CRHM"],"ready_for_planning":false,...} -->
```

The marker is untrusted input. `flowrun.promote_auto_choice()` parses and normalizes it, filters
KI names against the local catalogue and applies the host readiness checks before moving the flow.

### 3.3 A distinct prompt/policy phase

For a flow-gated Auto-KI turn, `_chat_auto()` now constructs an intake-only system contract. It
does **not** include the legacy Auto-KI execution rules, project-preparation rules, calibration
instructions or the old scope/approval script. Both direct API and CLI replay paths receive the
same intake system contract.

The flow state remains `RESOLVING_KIS` internally for compatibility, but its UI display stage is
now `understanding`, not `choosing_ki`.

### 3.4 Semantic fields survive into planning

After a valid intake, `flowrun.turn()` merges the normalized semantic fields into the plan intent.
The planning Agent no longer has to reconstruct the study area, process and requested outputs from
a short session title or a year/coordinate regex.

### 3.5 Important current boundary

The new semantic intake is currently guaranteed for the **free-language/Auto-KI entry path** (the
path in the reproduced screenshot). A session with a KI explicitly pinned in the UI still has a
fast path from host KI resolution into planning. The planning contract remains gated and safe, but
that pinned path does not yet persist the same rich intake object before the draft is derived.

If product policy is that *every* new scientific task, including a pinned-KI task, must pass through
semantic intake, the next repair should remove that fast path, carry the pinned KI as a preference,
and update the pinned-flow regression tests. Do not silently claim this has already been done.

---

## 4. Source-code map

### 4.1 Desktop application and HTTP orchestration

| Path | Responsibility | Relevant current work |
|---|---|---|
| `kiss/kiss_cli/gui.py` | Local HTTP server, chat endpoints, streaming, provider dispatch, Agent status, setup flow and Web UI data | `_stream_session_chat()` owns a chat turn; `_chat_auto()` now builds the intake-only contract; `_chat_with_models()` runs planning/execution turns |
| `kiss/kiss_cli/sessions.py` | Session index, transcript, project-folder creation, catalogue prompt and legacy Auto-KI rules | `catalogue_block()` supplies the local KI catalogue; `AUTO_RULES` is intentionally excluded from gated intake |
| `kiss/kiss_cli/projectrun.py` | Durable UI-facing project progress and Agent progress normalization | `_intake()` normalizes semantic handoff fields; `project-run.json` records intake; flow-owned stages cannot be changed by Agent reports |
| `kiss/kiss_cli/projectview.py` | Safe rendering metadata for project artifacts/results | Reads project artifacts; it is not execution evidence by itself |
| `kiss/kiss_cli/setup.py` | Setup requests and user-action popup lifecycle | A pending request prevents intake promotion and later execution transitions |
| `kiss/kiss_cli/web/app.html` | Main chat UI | Displays the project stage, Agent activity, data readiness and messages |
| `kiss/kiss_cli/web/library.html` | KI library UI | Lists and opens KI packages; separate from task intake |
| `kiss/kiss_cli/web/setup.html` | Model setup/verification UI | Software installation and preflight, not scientific execution |
| `kiss/kiss_cli/web/observatory.html` | Read-only KI Observatory and live-project visualization | Observes recorded DAG/project state; does not run KI code |
| `kiss/kiss_cli/web/studio.html` | KDT Workbench UI | KI creation/dissection workflow; separate from runtime task intake |

### 4.2 Agent/provider adapters

| Path | Responsibility | Relevant current work |
|---|---|---|
| `kiss/kiss_cli/api.py` | Direct API provider loop and typed tool proxy | `report_project_progress` schema now accepts `intake`; flow filters tools by state and rechecks every call |
| `kiss/kiss_cli/providers.py` | Native CLI provider definitions, subprocess streaming, session resume and structured activity events | Claude/Codex/Kimi receive the replay contract and native permission arguments |
| `kiss/kiss_cli/policy.py` | Desktop path permissions and provider-specific grants | Works with flow policy; do not confuse a prompt rule with an enforced path/tool boundary |
| `kiss/kiss_cli/prompt.py` | KI harness prompt composition | Builds inspect/execute/edit harness contracts for selected KI packages |
| `kiss/kiss_cli/harness_runtime.py` | Loads and proves the actual bundled `ki_tools_common` harness implementation | `harness-status` is the frozen-app proof command |

### 4.3 Desktop flow adapter and enforcement boundary

| Path | Responsibility | Relevant current work |
|---|---|---|
| `kiss/kiss_cli/flowrun.py` | Desktop adapter for resolution, intake promotion, planning, review, approval, setup, execution and verification | `pre()`, `auto_turn()`, `_intake_from_reply()`, `promote_auto_choice()`, `turn()` and `after()` form the lifecycle |
| `kiss/kiss_cli/flowgate.py` | Host-side tool/state gate around the shared flow package | Filters API tools, checks calls again at execution, validates plan bindings and records receipts |

### 4.4 Shared KI harness and flow package

| Path | Responsibility | Relevant current work |
|---|---|---|
| `ki_tools_common/ki_tools_common/harness/ki_harness.py` | Shared KI execution/inspect/edit contract | Must be loaded from the bundled package, not a four-line fallback |
| `ki_tools_common/ki_tools_common/flow/states.py` | Authoritative flow states, legal transitions, evidence requirements and capabilities | `RESOLVING_KIS` is read-only and now displays as task understanding |
| `ki_tools_common/ki_tools_common/flow/resolve.py` | Catalogue-name and coupling detection | Multilingual ASCII model-token extraction fixes the embedded-CRHM symptom; resolution is only a hint before Agent understanding |
| `ki_tools_common/ki_tools_common/flow/plan.py` | Draft plan/data-inventory derivation, schemas, validation and hashes | Receives the semantic intake fields through `flowrun.turn()` |
| `ki_tools_common/ki_tools_common/flow/contracts.py` | Planning and execution prompt contracts | Keeps inspect/planning separate from execution |
| `ki_tools_common/ki_tools_common/flow/policy.py` | State-specific provider tool/path policy | Intake/resolution is read-only; only planning draft files are writable in planning |
| `ki_tools_common/ki_tools_common/flow/tools.py` | Valid KI tool discovery/containment | Prevents arbitrary project scripts from being treated as trusted KI tools |
| `ki_tools_common/ki_tools_common/flow/approval.py` | Signed approval documents and drift checking | Binds approval to the current plan and inventory hashes |
| `ki_tools_common/ki_tools_common/flow/receipts.py` | Download/run receipts and evidence aggregation | A claim or plot is not a run receipt |
| `ki_tools_common/ki_tools_common/flow/build_data.py` | Bundled planning metadata/data-card support | Used by draft derivation when server planning data are unavailable |

### 4.5 KI packages, manifests and KDT

| Path | Responsibility |
|---|---|
| `models/<KI>/` | Portable KI package: `SKILL.md`, DAG, diagnostics, tools, documentation and optional visualization contract |
| `kiss/manifests/*.yaml` | Desktop installation/acquisition metadata for scientific software |
| `kiss/kiss_cli/kdtstudio.py` | KDT Workbench backend: source acquisition, dissection, candidate validation and import |
| `kiss/kiss_cli/observatory.py` | Safe projection of KI DAGs and visualization contracts into the Observatory |
| `kiss/vendor/agent-calibration-framework/` | Fixed shared calibration engine; not generated by a per-project Agent |

### 4.6 Packaging, release information and tests

| Path | Responsibility |
|---|---|
| `kiss/GeoForgeDesktop.spec` | macOS PyInstaller bundle, resources and hidden imports |
| `kiss/GeoForgeDesktopWindows.spec` | Windows frozen build specification |
| `kiss/pyproject.toml` | Canonical application version and Python package metadata |
| `ki_tools_common/pyproject.toml` | Shared harness/flow package metadata |
| `release-manifest.json` | Machine-readable update information used by update Agents |
| `DESKTOP_CHANGELOG.md` | Human-readable bilingual release explanation |
| `kiss/tests/test_flowrun.py` | Desktop flow/intake/planning/execution integration tests |
| `kiss/tests/test_flowgate.py` | Host-side state/tool/receipt enforcement tests |
| `ki_tools_common/tests/flow/test_flow_core.py` | Shared state, resolution, planning, approval and evidence tests |
| `kiss/tests/test_bundled_harness.py` | Proves the expected harness contract surface and import path |

---

## 5. Runtime file ownership inside one chat project

These files are deliberately separate. Do not merge Agent self-report with host authority.

| Runtime file | Writer/authority | Purpose |
|---|---|---|
| `runs/flow-state.json` | GeoForge flow only | Authoritative state, selected KIs, approval hashes and enforcement level |
| `runs/project-run.json` | GeoForge normalization layer | UI-facing stage/status/summary, selected KIs and normalized intake |
| `runs/project-agent-status.json` | Native CLI Agent when its current policy allows it | Untrusted progress handoff; cannot move a flow-owned stage |
| `setup-request.json` | Typed API tool or allowed setup/chat handoff | One structured request for a user decision, login, licence, file or permission |
| `runs/plan.json` | Planning submission, then host validation | Proposed scientific workflow; not permission to execute |
| `runs/data-inventory.json` | Planning submission, then host validation | Required/resolved/missing data and provenance plan |
| `runs/approval.json` | GeoForge approval module | Signed user/auto approval bound to exact plan and inventory hashes |
| `runs/receipts/*.json` | Host receipt layer | Evidence for declared downloads and KI tool/model executions |
| `runs/evidence.json` | Host verification layer | Final aggregation of receipt and output-validation results |
| `inputs/` | Execution phase only, through approved paths/tools | Scenario source and prepared scientific inputs |
| `outputs/` | Execution phase only | Scientific model output |
| `artifacts/` | Agent/app after real content exists | Plots, reports and project views; not proof by themselves |

---

## 6. Files changed for this intake repair

The focused repair touches or adds logic in:

- `ki_tools_common/ki_tools_common/flow/resolve.py`
  - added `_ASCII_MODEL_TOKEN`;
  - unknown-model analysis no longer consumes an entire Chinese sentence.
- `ki_tools_common/ki_tools_common/flow/states.py`
  - `RESOLVING_KIS` displays as `understanding`.
- `kiss/kiss_cli/projectrun.py`
  - added normalized `intake` state;
  - documents intake fields in Agent progress instructions.
- `kiss/kiss_cli/api.py`
  - added the typed `intake` schema to `report_project_progress`.
- `kiss/kiss_cli/flowrun.py`
  - free-language scientific requests enter Agent intake instead of host-authored model questions;
  - added the CLI `GEOFORGE_INTAKE` parser;
  - validates readiness before planning;
  - merges semantic intake fields into plan intent.
- `kiss/kiss_cli/gui.py`
  - separates gated intake prompts from execution/preparation prompts;
  - makes API and CLI receive the same system contract;
  - promotes only a validated intake handoff.
- `ki_tools_common/tests/flow/test_flow_core.py`
  - multilingual embedded-model regression tests.
- `kiss/tests/test_flowrun.py`
  - Chinese CRHM intake tests;
  - unknown-model Agent clarification test;
  - semantic-intent persistence test;
  - actual Handler/API contract-path regression test.
- `DESKTOP_CHANGELOG.md` and `release-manifest.json`
  - release/update explanation for the task-intake change.

This list does **not** imply that every modified file in the working tree belongs to this narrow
repair. The branch contains substantial earlier Desktop, Observatory, KDT, setup, proxy, manual and
KI work.

---

## 7. Validation completed

Full local source suite:

```bash
PYTHONPATH=kiss:ki_tools_common python3 -m pytest -q --import-mode=importlib \
  kiss/tests ki_tools_common/tests/flow
```

Result:

```text
306 passed, 3 skipped, 1 warning in 44.02s
```

The warning is the existing local NumPy/NetCDF binary-compatibility warning; this task does not
claim to repair that environment warning.

Focused task-intake checks cover:

- `CRHM` embedded in a Chinese sentence;
- unknown `CaMa` handled by the Agent intake rather than a host regex question;
- incomplete intake remains in the understanding phase;
- contradictory `ready=true` plus non-empty `missing` is rejected;
- study area, period, process and requested outputs survive into the plan intent;
- the real `_chat_auto()` direct API seam receives the intake contract;
- gated intake excludes legacy preparation/execution contracts.

Frozen macOS build:

```text
kiss/dist-task-intake-v0.6.49/GeoForge Desktop.app
```

Checks completed:

- PyInstaller build succeeded;
- `codesign --verify --deep --strict` passed;
- frozen `harness-status CRHM` returned `ready: true`;
- harness marker: `[KI HARNESS v1]`;
- frozen harness implementation SHA-256:
  `2c71f65452555f37c3a38b4216ca8f79a401ac81d59ac30befdfd977fa8dd5e8`;
- frozen launcher SHA-256:
  `712a8d940de4f2bdf3a17ab9d9bb74e55c41dc45a03e5fd377d31f577db1f61c`.

---

## 8. Manual acceptance test

Use a **new Auto-KI chat** so old provider/session state cannot confuse the observation.

Input:

```text
我想要用 CRHM 模拟中国高寒区融雪径流。
```

Expected first phase:

1. The UI says it is understanding the task, not merely selecting a model.
2. The Agent retains `CRHM`, the Chinese alpine context and the snowmelt-runoff process.
3. It does not claim that the whole sentence is an unknown model.
4. If the exact basin or simulation period materially affects the plan, it asks for those facts.
5. No download, input generation, installation, plan write or model run occurs in this phase.
6. After the missing facts are supplied, the Desktop validates the structured intake and only then
   begins a separate planning turn.

Inspect these files during the test:

```text
<project>/runs/flow-state.json
<project>/runs/project-run.json
<project>/runs/plan.json                  # must not exist before promotion/planning
<project>/runs/data-inventory.json         # must not exist before promotion/planning
```

Repeat with DeepSeek API, Claude Code, OpenAI Codex and Kimi Code. The source regression proves the
contract path, but a live acceptance matrix for this exact intake revision has not yet been recorded.

---

## 9. Working-tree and release safety

The current `mac-version` worktree is intentionally very dirty. It includes earlier user/local work,
generated builds, manuals, acceptance evidence, downloaded examples and stress-test material.

Do **not**:

- run `git reset --hard` or `git clean`;
- remove untracked build/evidence folders without resolving their ownership;
- stage every modified/untracked file as one commit;
- assume `git diff` shows all important code: the shared `flow/` package and several tests are
  currently untracked in this checkout;
- push the 407 MB `.app` directory directly into Git.

Before committing, explicitly construct the intended file list, inspect it and separate source,
documentation, generated artifacts and unrelated user changes. The current intake build has **not**
been pushed to `mac-version` or `main`.

The canonical KI library updater still targets `main`; platform branches carry Desktop code/builds.
Do not use the platform branch as the KI source without an explicit override.

---

## 10. Recommended next steps

1. Run the four-provider live acceptance matrix for the exact CRHM Chinese prompt and retain only
   public prompts, tool/activity events and host state files.
2. Decide whether pinned-KI sessions must also pass through the same semantic intake phase. If yes,
   carry the pinned KI as an Agent preference instead of using the current fast path.
3. Localize the short inter-phase message (`Task understood · KI ... · Building the plan`) instead
   of leaving it hard-coded in English.
4. Add an explicit UI card that shows the normalized task understanding and material missing facts,
   so the user can correct them before plan generation.
5. Confirm the same flow package and Desktop adapter behavior in a rebuilt Windows executable.
6. Update the manual screenshots only after the final intake UI wording is stable.
7. Make a scoped source commit, rebuild, regenerate checksums/release notes and push only after the
   file list and branch destination have been reviewed.

---

## 11. Core design rule for future work

Keep four kinds of truth separate:

1. **Agent understanding** — semantic interpretation and proposed choices;
2. **Desktop state** — legal phase and permissions;
3. **user approval** — authorization bound to exact artifacts; and
4. **scientific evidence** — real data, process receipts and validated outputs.

No one layer substitutes for another. Loading the KI harness is necessary, but the Desktop must
still enforce the lifecycle around it.
