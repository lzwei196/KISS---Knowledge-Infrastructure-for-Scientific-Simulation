# GeoForge Desktop source review handoff

Date: 2026-09-01  
Repository: `lzwei196/KISS---Knowledge-Infrastructure-for-Scientific-Simulation`  
Local branch: `mac-version`  
Local base commit at review: `9a42d0b`  
Status: **review only — no source file was modified by this pass**

This document records an independent read of the GeoForge Desktop source at commit `9a42d0b`
with the working tree in its current (intentionally dirty) state. It is a companion to
[`GEOFORGE-DESKTOP-TASK-INTAKE-HANDOFF-2026-09-01.md`](GEOFORGE-DESKTOP-TASK-INTAKE-HANDOFF-2026-09-01.md),
which describes the task-intake repair itself. That handoff was read before finalizing this one,
and two findings below are corrections to conclusions drawn before it was read.

Every claim in sections 3–6 was reproduced against the working tree. Commands are given so the
next reader can re-verify rather than trust this document. Section 8 states what was **not**
reviewed, so that absence of a finding is not read as evidence of correctness.

---

## 1. Scope of this review

Reviewed:

- `kiss/kiss_cli/` — HTTP server, routing, agent loop, tool layer, provider adapters, frontend
- `ki_tools_common/ki_tools_common/` — shared harness, `flow/` package, numerics library
- `.github/workflows/release.yml`, both `pyproject.toml` files, `.gitignore`, git history and worktree state

Method: full source read of the server/tool/frontend layer; test-suite execution; targeted
reproduction scripts for suspected defects; `pyflakes` sweep; git object and worktree inspection.

Not reviewed — see §8.

---

## 2. Assessment

The parts of this codebase that normally fail are **not** failing here, and effort should not be
spent re-hardening them:

| Area | State | Evidence |
|---|---|---|
| Path confinement | Correct | `api.py:685` resolves then verifies containment; `..` and symlinks both rejected; applied consistently across four roots (`_inside`, `_inside_work`, `_inside_project`, `_ki_scoped`) |
| Zip extraction | Correct | `ki_updates.py:295` and `gui.py:2657` (`_import_ki_bytes`) both reject traversal, cap file count and expanded size, and validate symlink targets against the snapshot root. No zip-slip, no zip bomb |
| Chat XSS | Correct | `md()` (`web/app.html:510`) escapes **before** applying markdown regexes; artifacts served with `default-src 'none'; sandbox` + `nosniff` |
| Child-process env | Correct | `API_KEY` / `TOKEN` / `SECRET` / `PASSWORD` / `CREDENTIAL` stripped at `api.py:866` |
| Session persistence | Correct | `sessions.save` uses tmp-then-replace with a per-session lock (`sessions.py:316`) |
| Intake marker parsing | Correct | `ready_for_planning is True` identity check; KI names filtered against the local catalogue; host readiness checks applied after (`flowrun.py:676`) |

Source comments are unusually good: they record the *failure that motivated the code* rather than
restating it. Preserve that convention.

The defects below cluster in three places: the **numerics library** (no test gate), the
**worktree/git state** (the enforcement layer is not committed), and **`gui.py`'s size** (a
358-line router already contains one latent crash).

---

## 3. Finding A — the `flow/` enforcement package is not in version control

**Severity: highest. This is the item to act on first.**

§9 of the task-intake handoff notes in passing that "the shared `flow/` package and several tests
are currently untracked." The concrete extent:

```bash
git ls-files ki_tools_common/ki_tools_common/flow/     # -> 0 files
git ls-files ki_tools_common/tests/flow/               # -> 0 files
```

Compared against `origin/flow-gate`, the only ref carrying any version of this package:

| module | remote | local | state |
|---|---|---|---|
| `contracts.py` | 235 | 244 | diverged |
| `plan.py` | 707 | 746 | diverged |
| `policy.py` | 290 | 303 | diverged |
| `resolve.py` | 268 | 277 | diverged |
| `states.py` | 255 | 259 | diverged |
| `tools.py` | — | 39 | **absent from every remote**; recoverable from local branch `codex/ki-harness-plan-handoff` (byte-identical) |
| `__init__.py`, `approval.py`, `build_data.py`, `receipts.py` | = | = | same line count (not diffed) |

`tools.py` is the module §4.4 of the intake handoff describes as *"prevents arbitrary project
scripts from being treated as trusted KI tools."* Layers 2, 3 and 4 of the intake handoff's §11
design rule — Desktop state, user approval, scientific evidence — exist in their newest form only
in this working tree and (for `tools.py`) on one unpushed local branch. No remote carries them.

**Correction (2026-09-01, post-verification):** an earlier draft of this row said `tools.py`
"exists on no branch, local or remote." That was wrong — it is on `codex/ki-harness-plan-handoff`
and is byte-identical to the working copy. Finding A stands (a clean `mac-version` checkout still
cannot build), but `tools.py` is recoverable.

### Why the existing §9 warning cannot hold this

`flow/` sits at roughly position 10 of ~66 untracked entries, interleaved with 38 `build-*` /
`dist-*` directories, `acceptance/` (~2 GB of GeoTIFFs), `GeoForge Desktop.app/` (407 MB) and
`.stress-kimi/`. §9 correctly forbids `git add -A`. But the inverse risk is equally live: **the
only way to commit the enforcement layer today is to hand-pick it out of a 66-item list in which
most entries must never be committed.** That is a manual selection under pressure.

### Recommended fix — mechanism, not warning

This deletes nothing and is fully compatible with §9's "do not `clean`, do not `reset --hard`":

```bash
printf '%s\n' 'build-*/' 'dist-*/' '.pyinstaller-*/' '*.app/' 'acceptance/' '.stress-kimi/' >> .gitignore
```

`.gitignore` currently has `build/` and `dist/`, which do **not** match `build-v0.6.39` or
`dist-task-intake-v0.6.49`. After this change `git status` drops from ~66 untracked entries to
roughly six, `flow/` and `tests/flow/` become visible rather than buried, and a scoped commit
becomes reviewable. Commit `flow/` and `tests/flow/` as their own commit, separate from the
task-intake source changes.

Related git-state facts (context, not blockers):

- `.git` is **6.3 GB**. History contains ~1.8 GB of GeoTIFFs from a single CRHM acceptance run
  (`dem_filled.tif` alone is 593 MB) and ~1 GB of `.app.zip` release binaries across v0.6.18–0.6.24.
  The README instructs users to `git clone`; they currently pay 6 GB for a pip-installable package.
  A `git filter-repo` pass and moving binaries to Release assets would fix this, but it rewrites
  history and must be coordinated across `main`, `mac-version`, `windows-version` and `flow-gate`.
- 38 `build-*` / `dist-*` directories occupy ~13 GB in the worktree.

---

## 4. Finding B — the "invisible" intake marker is rendered to the user

**Severity: high. Directly affects the acceptance matrix in §8 of the intake handoff.**

§3.2 of the intake handoff has CLI providers terminate their reply with
`<!-- GEOFORGE_INTAKE {...} -->`. The prompt at `gui.py:3167` calls it "one invisible marker."

The marker is **instructed** (`gui.py:3167`) and **parsed** (`flowrun.py:666`). It is never
stripped. Those are the only three occurrences in the entire source tree:

```bash
grep -rn "GEOFORGE_INTAKE\|INTAKE_MARKER" kiss/kiss_cli/*.py kiss/kiss_cli/web/*.html kiss/kiss_cli/web/*.js
# flowrun.py:32, flowrun.py:666, gui.py:3167  — no strip anywhere
```

Consequences:

1. The marker is streamed to the browser through `out(piece)` and appended to `buf`.
2. `buf` is persisted to the session transcript, so it survives reload and appears on every replay.
3. `md()` calls `esc()` **first** (`web/app.html:510`), converting `<` to `&lt;` before anything
   could treat the text as an HTML comment. It therefore renders as **literal visible text**, not
   as a comment.

The user sees this appended to every Auto-KI first-turn reply on Claude Code, Codex and Kimi — the
three CLI providers named in the intake handoff's §8 acceptance matrix, on exactly the screenshot
path §1 is repairing:

```text
<!-- GEOFORGE_INTAKE {"selected_kis":["CRHM"],"ready_for_planning":false,
"understanding":"...","missing":["exact basin or spatial boundary"]} -->
```

§8's manual test directs the tester to inspect `runs/flow-state.json`, `runs/project-run.json`,
`runs/plan.json` and `runs/data-inventory.json`. Nothing directs them at the chat bubble, so the
acceptance matrix as written can pass while this defect ships.

### Recommended fix

`extractWork()` in `web/app.html:477` already solves exactly this problem for `[[GEOF_TOOL:...]]`
and `<invoke>` blocks. Apply the same treatment, in two places:

1. **Server-side, before `buf` is persisted** — this is the important one, because the transcript is
   durable and a client-only fix leaves every already-saved transcript dirty.
2. **In `extractWork()`** as defence in depth, so older saved conversations render cleanly too.

### Secondary note on the same seam

`_intake_from_reply` iterates `reversed(...)`, so the **last** marker in the reply wins. If an agent
quotes a KI document or an uploaded paper that contains a forged marker after its own, the forged
one is read. The catalogue filter and the host readiness checks contain the blast radius, and the
marker is agent-authored rather than attacker-authored, so this is low severity — but **first**
marker wins would be strictly safer and is a one-word change.

---

## 5. Finding C — two silent domain errors in `netcdf_utils`

**Severity: high. Produces wrong scientific inputs with no error, no warning, and a clean receipt.**

Both defects are the same root cause: longitude convention is never reconciled between the request
and the dataset. In `bbox_subset` the fingerprint is explicit — `lon_vals` is read at
`netcdf_utils.py:170` and then never used, while the two lines above it carefully handle
descending-latitude grids.

### C1 — `bbox_subset` silently truncates or empties the domain

`ki_tools_common/ki_tools_common/netcdf_utils.py:130`

Reproduced on an ERA5-shaped grid (0–360 longitude, descending latitude):

```text
requested lon -10 .. 5   (15° wide)  ->  returned 0.0 .. 5.0   (5° wide)
requested lon -30 .. -5              ->  returned 0 points
```

No exception is raised, because `xarray`'s `.sel` with a slice returns an empty selection rather
than failing. ERA5, CMIP6 and GFS all publish 0–360 longitude, so this is the common case.

Three distinct bugs in one function: the 0–360 vs −180–180 convention, descending-longitude grids
(latitude is handled, longitude is not), and antimeridian wrap.

### C2 — `basin_mask_from_shapefile` returns an all-False mask

`ki_tools_common/ki_tools_common/netcdf_utils.py:221`

Worse than C1, because the failure is total rather than partial. The function builds
`Point(lon, lat)` from raw dataset longitudes and tests containment against shapefile geometry.
Shapefiles are effectively always −180..180. Reproduced with an identical basin polygon, identical
resolution, and only the dataset's longitude convention changed:

```text
dataset lon 0 .. 360      -> 0 cells selected      (silently empty mask)
dataset lon -180 .. 180   -> 16 cells selected     (correct)
```

Any Western-hemisphere basin against an ERA5-convention dataset yields a completely empty mask. A
basin spanning the prime meridian loses half its cells.

**C2 has live in-repo callers**, unlike C1: `load_cmfd_forcing` (line 286) and `load_mswx_forcing`
(line 380) both consume this mask. The full failure chain was traced and reproduced:

```text
all-False mask
  -> data[:, mask]              shape (time, 0)
  -> np.nanmean(spatial, axis=1)  all-NaN, emits only a numpy RuntimeWarning
  -> all_values.extend(daily_vals)
  -> `if not all_values:` guard does NOT fire — the list is full, of NaN
  -> returns a full-length all-NaN forcing time series
```

The `FileNotFoundError` guard at line 322 exists precisely to catch "no data," and it does not fire,
because the array is populated with NaN rather than empty. The only signal is a numpy
`RuntimeWarning: Mean of empty slice` in stdout.

Exposure by dataset: **CMFD is safe by coincidence** — it covers China at 70–140°E, where the two
longitude conventions agree. **MSWX is global and is exposed.** Any MSWX basin west of Greenwich
silently produces NaN forcing.

(Performance of the per-cell Python loop was measured and is acceptable — ~4 s for a full
1,038,240-cell ERA5 grid. Not a concern; correctness is.)

### Why the evidence architecture cannot catch this

The intake handoff's §5 gives `runs/receipts/*.json` authority over `inputs/`. A receipt proves a
tool *ran*; it cannot prove the tool produced the right spatial domain. For both C1 and C2 a receipt
is written, `evidence.json` aggregates cleanly, and approval hashes match — while the simulation runs
on the wrong basin. This is not a hole in the evidence design; it is the boundary of what receipts
can assert, and it is the argument for Finding D.

### Recommended fix

For both functions: normalize the requested longitudes into the dataset's own convention, mirror the
existing descending-latitude handling for longitude, handle antimeridian wrap by concatenating two
slices, and **raise on an empty result instead of returning it**. A subsetter or masker that can
return nothing silently is a trap independent of the convention bug.

### Current blast radius

- **C1 (`bbox_subset`)** has no in-repo callers — verified by grep across `ki_tools_common`, `kiss`
  and `models`. It is exported from the wheel and documented in the module docstring for KI tool
  authors, so agents will find and call it, but nothing shipping invokes it today.
- **C2 (`basin_mask_from_shapefile`)** is called by `load_cmfd_forcing` and `load_mswx_forcing` in
  the same module. This is a live path, mitigated only by CMFD's China-only extent. Fix C2 first.

---

## 6. Finding D — the numerics library has no test gate

**This finding corrects an earlier, wrong conclusion.** A first pass judged that `ki_tools_common`
had "zero CI coverage." That is false as stated: the intake handoff's §7 command reproduces exactly.

```bash
PYTHONPATH=kiss:ki_tools_common python3 -m pytest -q --import-mode=importlib \
  kiss/tests ki_tools_common/tests/flow
# 306 passed, 3 skipped, 1 warning in 44.57s
```

The `flow/` enforcement layer is genuinely well tested. The gap is the **numerics**:

| suite | tests | runtime | invoked by |
|---|---|---|---|
| `kiss/tests` | 232 | 40 s | CI (`release.yml:37`) **and** §7 command |
| `ki_tools_common/tests/flow` | 74 | 2.5 s | §7 command only — **not CI** |
| `ki_tools_common/ki_tools_common/tests` | 93 | **0.26 s** | **nothing** |
| `ki_tools_common/tests/test_{debug_framework,units,climate_scenarios}.py` | — | — | broken collection |

Three structural problems:

1. **`ki_tools_common/pyproject.toml:47` declares `testpaths = ["tests"]`**, which cannot be
   collected. `ki_tools_common/tests/test_debug_framework.py:16` does a flat
   `from debug_framework import (...)` that resolves under no invocation, including with
   `--import-mode=importlib` and `PYTHONPATH` set. One broken tracked file poisons collection of its
   whole directory — which is precisely why §7's command must target `tests/flow` rather than `tests`.

2. **Two divergent test trees both named `tests`.** `ki_tools_common/tests/` (3 science files,
   tracked, broken) and `ki_tools_common/ki_tools_common/tests/` (7 files, tracked, 93 passing). Both
   are Python packages named `tests` and both contain a `test_units.py` whose contents differ, so
   they can never be collected in the same run. Running pytest from the repo root fails outright with
   6 collection errors. The inner tree also ships inside the wheel, since
   `[tool.setuptools.packages.find] include = ["ki_tools_common*"]` matches it.

3. **CI runs `pytest kiss/tests` only** (`release.yml:37`) — 232 of the 399 available tests. The 74
   flow tests guarding the enforcement boundary run only when a human remembers the
   `--import-mode=importlib` incantation.

Net: `units.py` (1,065 lines), `metrics.py` (655), `load_forcing.py` (1,216),
`debug_framework.py` (1,772) and `climate_scenarios/` are gated by nothing. Finding C lives exactly
in that gap.

### Recommended fix

Fix or delete `tests/test_debug_framework.py`'s import, choose one home for the science tests, and
extend the CI line to all three paths. The 93 orphaned tests run in **0.26 seconds** — the cost of
closing this is negligible and it is what makes Finding C catchable next time.

---

## 7. Lower-severity findings

Each is small and independently fixable. None blocks a release.

### 7.1 Latent crash in the `do_POST` router — `gui.py:1864`

`/api/import_ki` is handled twice. Line 1517 returns unconditionally, so the second handler at 1864
is unreachable. It calls `self._import_ki(req)` — **a method that does not exist on `Handler`**
(verified by grep). Today it is dead. Any future edit that adds an early return above line 1517, or
reorders the chain, arms an `AttributeError` on a user-facing upload path.

This is a symptom of §7.5 rather than an isolated bug: a 358-line `if route == ...` chain cannot
surface a duplicate. A dispatch table (`{("POST", "/api/import_ki"): self._import_ki_bytes}`) would
have made it a duplicate-key error at import time.

### 7.2 No `Origin` check on any route — `gui.py:691`

There is no `Origin`, `Referer`, `Host` or `Sec-Fetch-Site` validation anywhere in `gui.py`, across
69 routes. `do_POST` parses the body as JSON regardless of `Content-Type` (`gui.py:1594`), so a
cross-origin `fetch(url, {method:'POST', mode:'no-cors', body: JSON.stringify(...)})` is a *simple
request* — no preflight — and the side effect lands even though the response is opaque.
`/api/chat` drives the agent; `/api/settings` overwrites API keys and proxy configuration.

Exposure differs by launch path:

- **Packaged `.app`** — `app.py:192` uses an **ephemeral loopback port**. A real and evidently
  deliberate mitigation; an attacker must port-scan localhost first.
- **`kiss gui`** — fixed default port **8765** (`cli.py:501`). This is the path the README documents
  for from-source use and the only path on Linux and Windows.

`serve()` already prints a careful warning for non-loopback binds. The fixed-port loopback case is
the one actually reachable from a browser. Cheapest fix: reject any request whose `Origin` header is
present and is not the server's own, and mint a per-launch nonce into the served page.

Note this boundary does not appear in the intake handoff's §11 four-layer model. All four layers
describe truth *inside* the app; there is no layer for "is this request from the app's own UI."

### 7.3 `settings.save` — key file mode race and silent key loss — `settings.py:51`

Two defects that `sessions.save` gets right 250 lines away:

- `p.write_text(...)` at line 58 creates the file under the process umask (typically `0o644`), then
  `p.chmod(0o600)` at line 60. The API-key file is world-readable for that window. Use
  `os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600)`.
- It is not tmp-then-replace, and `load()` swallows `JSONDecodeError` and returns `{}`. An
  interrupted write therefore **silently erases every saved API key with no message to the user**.
  Apply the `sessions.save` pattern.

### 7.4 `_agent_run_snapshot` holds its lock only to fetch the reference — `gui.py:240`

`_LIVE_AGENT_RUNS_LOCK` is released after the dict lookup at line 240–241. The function then reads
~10 fields and **writes** `events["_file_evidence"]` at line 278 outside the lock, while the
streaming thread concurrently writes `last_transport_at` and `last_visible_output_at` (lines
2910–2913). CPython's per-op atomicity prevents corruption, but snapshots are torn and two concurrent
pollers race on `_file_evidence`. Given the function's docstring commits to never overstating agent
state, an inconsistent snapshot is on-point. Hold the lock across the read, or deep-copy under it.

Separately, `_LIVE_AGENT_RUNS` entries are never removed. Keyed by session id, so growth is bounded
by session count rather than turn count — a slow leak, not a severe one — but finished `Popen`
handles are retained for the process lifetime.

### 7.5 Structure

| file | lines | longest functions |
|---|---|---|
| `gui.py` | 3,831 | `do_GET` **595**, `do_POST` **358**, `_stream_session_chat` 321 |
| `api.py` | 1,552 | `execute_tool` **652**, `tool_schemas` **441** |
| `kdtstudio.py` | 1,582 | `build_prompt` 154 |

`Handler` is a single ~2,940-line class routing 69 endpoints through flat `if` chains. Only ~7 KB of
`gui.py`'s 191 KB is prompt text, so this is essentially all logic. §7.1 is the first observable
consequence.

Recommended before further `gui.py` work: extract `do_GET`/`do_POST` into a dispatch table and split
`Handler` by domain (sessions / setup / KDT / library). Every current fix must be threaded through a
600-line function, which is the condition under which fixes generate new defects.

### 7.6 Docstring overstates a workflow guard — `api.py:571`

`_guard_installation_only_command` allowlists `awk`, `find`, `git`, `curl`, `tar` and `pip` with no
argument inspection. `find -exec`, `awk 'BEGIN{system(...)}'` and `pip install` all reach arbitrary
execution. As **workflow discipline** — keeping the agent from running the science model during
install — this is fine and appropriate. But the docstring reads "Make the no-scientific-run contract
a tool boundary, not a suggestion," which invites the next reader to treat it as a sandbox. §4.2 of
the intake handoff already states the correct principle ("do not confuse a prompt rule with an
enforced path/tool boundary"); the docstring contradicts it. Reword only — no code change.

---

## 8. Not reviewed

Absence of a finding below is **not** evidence of correctness:

- The 127 KI packages under `models/` — `SKILL.md`, `dag.yaml`, diagnostics, per-KI tools
- `web/observatory.html` and the Observatory JavaScript; `library.html`, `setup.html`, `studio.html`
  beyond their `innerHTML` usage
- `calibration.py`, `vendor/agent-calibration-framework/`
- `kdtstudio.py` beyond its outline and function sizes
- `flow/` module internals beyond `resolve.py`, `states.py` and the `promote_auto_choice` seam
- Windows and Linux build paths; `GeoForgeDesktopWindows.spec`
- Any live provider run. **No API key was used and no agent turn was executed during this review.**
  Finding B in particular is derived from source reading and should be confirmed visually in one
  live CLI turn — it will take about one minute and is worth doing before §8 of the intake handoff
  is run in full.

---

## 9. Recommended order

Ordered by risk-reduction per unit of effort, not by severity alone.

1. **`.gitignore` the build/evidence directories, then commit `flow/` and `tests/flow/` as a scoped
   commit** (§3). Everything else on this list is rework if this disk fails. ~5 min plus review of
   the file list. Deletes nothing; compatible with intake-handoff §9.
2. **Strip the intake marker server-side and in `extractWork()`** (§4). Blocks intake-handoff §8
   from producing a clean acceptance result. ~15 min.
3. **Fix `tests/test_debug_framework.py`'s import; add both `ki_tools_common` test paths to
   `release.yml:37`** (§6). +168 tests for ~1 s of CI time. ~20 min.
4. **Fix both `netcdf_utils` longitude defects and make them raise on empty** (§5). ~1 h with
   regression tests, which item 3 makes durable. Do **C2 first** — it is on a live call path
   (`load_mswx_forcing`) and returns an all-NaN forcing series rather than an error. C1 has no
   in-repo callers yet. If item 3 slips, do C2 anyway.
5. `Origin` check plus per-launch nonce (§7.2). ~30 min.
6. `settings.save`: `os.open` with mode, tmp-then-replace (§7.3). ~10 min.
7. `_agent_run_snapshot` locking (§7.4). ~10 min.
8. Then intake-handoff §10's own list, and the `gui.py` router extraction (§7.5) before further
   large `gui.py` changes.

Items 1–3 total well under an hour and all three unblock the work the task-intake handoff is trying
to land.

---

## 10. Working-tree safety

The constraints in §9 of the task-intake handoff remain in force and were observed during this
review. Restating, because this document recommends a `.gitignore` change:

Do **not**:

- run `git reset --hard`, `git clean`, or remove untracked build/evidence folders;
- stage every modified or untracked file as one commit;
- assume `git diff` shows all important code — `flow/` and `tests/flow/` are untracked (§3);
- push the 407 MB `.app` directory into Git.

The `.gitignore` change recommended in §3 **removes nothing from disk**. It only stops ~60 generated
directories from appearing as commit candidates, so that `flow/` can be seen and committed
deliberately. Construct the intended file list explicitly and inspect it before staging.

This review modified no source file and made no git operation beyond read-only inspection.
