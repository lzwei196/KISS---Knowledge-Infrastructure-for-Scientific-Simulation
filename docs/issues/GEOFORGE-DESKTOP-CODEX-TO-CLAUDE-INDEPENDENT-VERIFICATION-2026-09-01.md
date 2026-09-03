# GeoForge Desktop: Codex-to-Claude independent verification handoff

Date: 2026-09-01  
Repository: `lzwei196/KISS---Knowledge-Infrastructure-for-Scientific-Simulation`  
Local branch: `mac-version`  
Local base commit: `9a42d0b`  
Status: **source-level verification completed by Codex and Claude; live-provider/UI checks remain
open; local implementation is not committed or pushed**

## 1. Purpose

This handoff asks Claude to independently verify two related bodies of work:

1. the local GeoForge Desktop task-intake implementation described in
   [`GEOFORGE-DESKTOP-TASK-INTAKE-HANDOFF-2026-09-01.md`](GEOFORGE-DESKTOP-TASK-INTAKE-HANDOFF-2026-09-01.md); and
2. the source-review findings originally recorded in
   [`GEOFORGE-DESKTOP-CODE-REVIEW-HANDOFF-2026-09-01.md`](GEOFORGE-DESKTOP-CODE-REVIEW-HANDOFF-2026-09-01.md).

Codex checked the review claims against the current working tree. This verification pass did
**not** fix the reported defects and did **not** make a source commit. The purpose of Claude's next
pass is to reproduce the evidence independently, challenge any incorrect conclusion, and state
which items block a clean release.

The worktree currently contains substantial user and earlier-Agent work. Do not infer ownership
from `git status`, and do not run `git clean`, `git reset --hard`, or a broad `git add -A`.

Verification progress after Claude's follow-up:

- Sections D-G have source-level or isolated-runtime reproductions from both reviewers, with the
  corrections recorded below.
- Section A is still open: no live Claude/Codex/Kimi/DeepSeek intake turn was run for this review.
- Section B is still open as a UI acceptance test: the marker defect is source-confirmed, but its
  streaming/completed/reloaded appearance has not been recorded from a live provider turn.
- Section C is decisive at the source layer: `git archive 9a42d0b` contains no `flow/` package and
  importing it raises `ModuleNotFoundError`. A complete clean-checkout PyInstaller build was not
  run.

## 2. Local implementation Claude must verify

The local task-intake repair claims the following behavior for a new free-language/Auto-KI
scientific chat:

```text
natural-language scientific goal
    -> read-only Agent task-understanding turn
    -> normalized intent + proposed KI(s) + material missing facts
    -> Desktop validates the handoff
    -> separate planning turn
    -> plan validation and review
    -> approval
    -> setup/execution
    -> evidence validation
```

Relevant local source changes are described in the task-intake handoff and currently involve:

- `ki_tools_common/ki_tools_common/flow/resolve.py`
  - extracts model-like ASCII identifiers from multilingual text;
  - should retain `CRHM` without treating the complete Chinese sentence as an unknown model.
- `ki_tools_common/ki_tools_common/flow/states.py`
  - presents `RESOLVING_KIS` as task understanding.
- `kiss/kiss_cli/projectrun.py`
  - normalizes and records the task-intake object.
- `kiss/kiss_cli/api.py`
  - permits the direct API progress tool to return `selected_kis` plus `intake`.
- `kiss/kiss_cli/flowrun.py`
  - starts Auto-KI scientific requests with Agent understanding;
  - validates the intake before planning;
  - merges semantic intent into the later plan.
- `kiss/kiss_cli/gui.py`
  - gives API and CLI providers an intake-only first-turn contract;
  - excludes preparation/execution instructions during intake.
- `kiss/tests/test_flowrun.py` and `ki_tools_common/tests/flow/`
  - contain the source-level regression coverage.

Important boundaries that must not be overstated:

- This semantic-intake path is guaranteed only for the free-language/Auto-KI entry path.
- A KI pinned in the UI still has a faster path into planning and does not yet persist the same
  rich intake object.
- Native CLI providers currently return intake through a textual HTML-comment marker. That marker
  is parsed, but it is not removed from the stream or saved transcript.
- The newest shared `flow/` implementation is present in the working tree but is not tracked on
  `mac-version`.

## 3. Codex's independent findings

### 3.1 Release durability: confirmed release blocker

On `mac-version` at `9a42d0b`:

```text
git ls-files ki_tools_common/ki_tools_common/flow ki_tools_common/tests/flow
-> 0 tracked files

git ls-tree -r --name-only origin/flow-gate -- the same paths
-> 252 older tracked files

all remote refs containing ki_tools_common/ki_tools_common/flow/tools.py
-> none

local branch codex/ki-harness-plan-handoff
-> contains an earlier complete flow snapshot: 241 data files, 10 modules and 4 test files
-> tools.py is byte-identical; resolve.py, states.py and test_flow_core.py differ from the working copy
```

The 252 files on `origin/flow-gate` are 241 `flow/data/` files, 9 flow modules and 2 flow-test
files. The large count must not be read as 252 enforcement modules.

The local branch is a recovery source, but it is not the current task-intake implementation. The
latest `resolve.py`, `states.py` and `test_flow_core.py` still exist only in the working tree.

The local PyInstaller build can succeed because `--add-data "ki_tools_common:ki_tools_common"`
copies untracked source from this machine. A clean checkout of `mac-version` cannot reproduce that
bundle. Claude should treat a successful existing `.app` as evidence about this working tree only,
not evidence of release reproducibility.

The current `.gitignore` ignores `build/` and `dist/`, but not versioned directories such as
`build-v0.6.49/`, `dist-task-intake-v0.6.49/`, or `.app` bundles. At verification time:

```text
.git                                      6.3 GB
acceptance/                               2.4 GB
individual dist directories              approximately 0.4-1.1 GB each
```

### 3.2 CLI intake marker: confirmed visible and durable

The marker is parsed by `flowrun._intake_from_reply()`, but `gui.py` streams every non-heartbeat
piece into `buf`, and later stores the complete `buf` as the assistant message. The frontend's
`extractWork()` removes tool markers but does not remove `GEOFORGE_INTAKE`. `md()` then HTML-escapes
the marker, turning it into visible text instead of an invisible comment.

The original review recommended making the *first* marker win instead of the last. Codex does not
consider that a sufficient security rule. Neither first nor last is unambiguous when quoted or
prompt-provided text can contain a marker. The safer temporary contract is:

- accept exactly one valid marker;
- reject or remain in intake when zero or multiple markers are present;
- strip the accepted marker from both the live stream and durable transcript; and
- migrate to structured provider output where the provider supports it.

### 3.3 NetCDF longitude and basin masking: confirmed scientific correctness defects

A synthetic reproduction produced:

```text
0..360 dataset + western (-10..-5) bbox       -> 0 longitude cells
descending longitude + (-8..8) bbox           -> 0 longitude cells
antimeridian bbox (170..-170)                  -> 0 longitude cells
western polygon on a 0..360 dataset            -> 0 selected mask cells
empty mask averaged over time                  -> [NaN, NaN]
bool(list([NaN, NaN]))                          -> True
```

Therefore `load_cmfd_forcing()` and `load_mswx_forcing()` can return an all-NaN series instead of
failing. The original review understated two adjacent cases that Claude should include:

- shapefile CRS is not checked or transformed to EPSG:4326; and
- coordinate aliases include WRF-style `XLAT`/`XLONG`, but `bbox_subset()` assumes one-dimensional
  ordered coordinates. This curvilinear case raises `ValueError` and therefore fails closed; it is
  a compatibility defect, not another silent-wrong-data path.

### 3.4 Shared tests and CI: confirmed integration gap

Observed locally:

```text
PYTHONPATH=ki_tools_common python3 -m pytest --collect-only -q ki_tools_common/tests
-> 159 tests collected, then test_debug_framework.py fails to import debug_framework

PYTHONPATH=ki_tools_common python3 -m pytest -q ki_tools_common/ki_tools_common/tests
-> 93 passed, 2 skipped

PYTHONPATH=ki_tools_common python3 -m pytest -q ki_tools_common/tests/flow
-> 74 passed, 2 skipped

PYTHONPATH=ki_tools_common python3 -m pytest -q kiss/tests/test_flowrun.py
-> 38 passed

PYTHONPATH=ki_tools_common python3 -m pytest -q \
  kiss/tests/test_flowrun.py ki_tools_common/tests/flow
-> 3 collection errors: tests.flow cannot be resolved after the other tests package is loaded
```

Using `--import-mode=importlib` allows the intended combined source suite to run, but that is a
workaround, not a coherent test-package layout. The release workflow currently runs only
`python -m pytest kiss/tests -q`; it does not gate the shared flow or numerical library.

### 3.5 Secondary source findings: confirmed, with different priorities

- `gui.py` has two `/api/import_ki` POST branches. The earlier raw-upload branch returns first; the
  later JSON branch is unreachable and calls a nonexistent `_import_ki` method.
- The localhost HTTP server has no Origin, CSRF-token, Host, or request Content-Type enforcement.
  In an isolated temporary workroot, an HTTP POST with `Origin: https://evil.example` and
  `Content-Type: text/plain` returned HTTP 200 and created a session on disk. This proves the server
  accepts the cross-origin-shaped request. A real browser `fetch(mode: "no-cors")` was not run in
  this verification, so browser transport remains an explicit live check rather than an inferred
  test result.
- `settings.save()` writes the API-key file before applying mode `0600`; the threaded server can
  also interleave two `load -> modify -> save` updates and lose one change. A concurrent isolated
  write/read reproduction observed 64 invalid JSON reads out of 125 and 52 occasions on which
  `settings.load()` silently converted the invalid file to empty settings. The final file happened
  to be valid; a reader during the write was not protected.
- `_agent_run_snapshot()` retrieves the shared event dictionary under a lock, then reads and
  mutates it after releasing the lock. Finished session entries have no TTL or removal policy.
- `gui.py` and `api.py` remain large orchestration modules. This is a maintainability finding, not
  proof of a user-visible defect by itself.
- The installation-only command guard is useful, non-shell and path-confined, but it is not a hard
  no-execution sandbox. `_guard_installation_only_command()` itself reaches an implicit allow for
  unmatched commands such as `bash`; the outer public `run_setup_command` allowlist blocks bare
  `bash`, `sh`, `env` and `xargs` before that function is reached. The public tool is nevertheless
  bypassable through an allowed program: `awk 'BEGIN{print system("false")}'` executed the child
  command and returned its status. `find -exec` and build-tool equivalents need the same semantic
  treatment. The current docstring promises a stronger boundary than the full implementation
  supplies.

### 3.6 Flow-package integrity proof: newly confirmed gap

`kiss/GeoForgeDesktop.spec` explicitly declares nine flow submodules: the seven lifecycle modules
plus `tools` and `build_data`. `flowgate.load()` imports and origin-checks only the seven lifecycle
modules. It therefore does not prove the full bundle declared by the build.

This matters for `tools.py`: `api.py` imports `ki_tools_common.flow.tools.is_ki_tool` only when
`run_ki_tool` is invoked. A package missing `tools.py` can pass `flowgate.load()` and then fail
closed later during a trusted-tool call. Add both declared modules to the startup integrity check,
and add a frozen-build test that exercises the trusted-tool discovery path rather than only
checking the package root.

## 4. Required independent verification by Claude

Claude should report `confirmed`, `not reproduced`, or `partially confirmed` for every item below.
Do not begin by patching; first preserve a reproducible failing observation.

### A. Verify the task-intake behavior end to end

Run a **new Auto-KI session** for each available provider:

- Claude Code;
- OpenAI Codex;
- Kimi Code; and
- DeepSeek API.

Use the exact first message:

```text
我想要用 CRHM 模拟中国高寒区融雪径流。
```

Verify all of the following:

1. `CRHM` is retained as the model preference.
2. The whole Chinese sentence is not treated as an unknown KI name.
3. The response summarizes the scientific intent and asks only materially necessary questions,
   such as the exact basin and simulation period.
4. The first turn performs no download, input generation, software installation, plan write, or
   model run.
5. `runs/flow-state.json` remains in `RESOLVING_KIS` until intake is complete.
6. `runs/project-run.json` records the normalized intake.
7. `runs/plan.json` and `runs/data-inventory.json` do not exist before promotion to planning.
8. Once missing facts are provided, the semantic study area, period, process, scenario and outputs
   survive into the generated plan intent.
9. Direct API providers receive the same intake-only contract as native CLI replay.
10. No legacy preparation/execution prompt is present during intake.

Repeat one test with CRHM explicitly pinned in the UI. Record the difference; do not report the
pinned path as equivalent unless it produces and validates the same intake object.

### B. Verify the marker defect in the real UI

For Claude Code, Codex and Kimi:

1. observe the message while it is streaming;
2. inspect the completed chat bubble;
3. reload the application and inspect the restored transcript;
4. inspect the stored session JSON; and
5. submit synthetic responses containing zero, one and two markers.

Expected current result: the single marker is visible and persisted. Independently decide whether
multiple markers should fail closed rather than using first- or last-marker precedence.

### C. Verify a clean-checkout build, not the existing local `.app`

Create a disposable checkout or `git archive` from `mac-version` at `9a42d0b`. Do not copy the
working tree's untracked `ki_tools_common/flow` directory into it.

Verify:

1. whether `ki_tools_common.flow` imports;
2. whether `flowgate.load()` fails closed;
3. whether the clean PyInstaller build contains the flow package;
4. whether `harness-status CRHM` proves the intended harness and flow implementation; and
5. whether `flow/tools.py` is present on any remote ref and whether it is recoverable from a local
   branch. Current result: absent from remotes, byte-identical on
   `codex/ki-harness-plan-handoff`; that local branch also contains an earlier full flow snapshot,
   but its `resolve.py`, `states.py` and `test_flow_core.py` are not the working-tree versions.

This check should distinguish “the local app works” from “the branch can reproduce the app.”

### D. Verify longitude, CRS and empty-data behavior

Add or run isolated tests for:

- ascending and descending latitude;
- ascending and descending longitude;
- request and dataset conventions of both `[-180, 180]` and `[0, 360)`;
- prime-meridian and antimeridian crossing;
- exact-boundary coordinates;
- one-dimensional and curvilinear coordinates;
- EPSG:4326 and projected basin shapefiles;
- an all-False basin mask; and
- all-NaN output from CMFD/MSWX loading.

A successful correction must either return the requested geographic domain or raise an explicit,
actionable exception. An empty subset or all-NaN forcing series must never count as success.

### E. Verify test topology in a fresh environment

Use a fresh virtual environment and explicitly install the package's declared test dependencies.
Report the commands and dependency set; do not rely on scientific packages already installed on
this Mac.

Check:

1. Desktop tests alone;
2. shared flow tests alone;
3. shared numerical tests alone;
4. all three trees in one invocation;
5. the behavior with and without `--import-mode=importlib`; and
6. the exact tests executed by `.github/workflows/release.yml`.

The proposed CI repair must install required package extras before adding these paths to the gate.

### F. Verify local HTTP and settings safety in isolation

Start the server with a temporary workroot and no real API keys. Use a harmless endpoint in that
isolated directory to determine whether a cross-origin `text/plain` POST is accepted without a
token. Also check Host and Origin handling for the embedded WebView's normal requests.

For settings, monkeypatch `settings._path()` to a temporary directory and verify:

- initial file mode during and after creation;
- atomicity under an interrupted write;
- two simultaneous updates to different fields; and
- whether one update can erase the other or lose an API key.

Do not test this against the user's real settings file.

### G. Verify state registry, dead routing and the setup command boundary

1. Exercise simultaneous snapshot polling while provider callbacks mutate their event record;
   check for inconsistent states and dictionary mutation outside the lock.
2. Create and finish many temporary sessions; confirm whether `_LIVE_AGENT_RUNS` grows without
   cleanup.
3. Prove the second `/api/import_ki` branch is unreachable and that `_import_ki` is undefined.
4. Test the installation-only guard only with inert temporary executables. Check whether
   `awk system(...)`, `find -exec`, or an allowed build target can execute a workspace program even
   though a direct invocation is rejected.

Never run a real scientific model for this guard test.

## 5. Expected report from Claude

Please return one table with these columns:

| Item | Independent verdict | Reproduction | User/scientific impact | Release blocker | Recommended fix |
|---|---|---|---|---|---|

The report should separately answer:

1. Does the task-intake implementation actually solve the original structural CRHM conversation
   problem for all four provider paths?
2. Which behavior differs between Auto-KI and pinned-KI sessions?
3. Can a clean `mac-version` checkout reproduce the locally built application?
4. Can any current forcing loader silently return geographically wrong or all-NaN data?
5. Are all enforcement and numerical tests executed by release CI?
6. Which HTTP/settings issues are exploitable versus merely theoretical under the packaged
   Desktop runtime?
7. Is the installation-only gate a policy aid or a security boundary?

Include exact command output for failures. Do not mark an item fixed based only on source reading.

## 6. Suggested repair order after independent agreement

1. Preserve and make reviewable the current shared `flow/` source and tests; ensure a clean branch
   can reproduce the enforcement package.
2. Repair longitude normalization, ordering, wrap, CRS handling and empty/all-NaN rejection; add
   numerical regression tests.
3. replace or sanitize the CLI intake marker and reject ambiguous handoffs.
4. unify test packaging and add shared flow/numerics to release CI with explicit dependencies.
5. add localhost request authentication/Origin validation and atomic locked settings persistence.
6. clean the dead import route and bound the live-Agent registry.
7. tighten or accurately describe the installation-only command boundary.
8. split HTTP routing and provider orchestration only after behavior is covered by tests.

No deletion, history rewrite, broad staging, commit, push, or release is authorized by this
handoff. Those actions require an explicit follow-up request and a reviewed file list.
