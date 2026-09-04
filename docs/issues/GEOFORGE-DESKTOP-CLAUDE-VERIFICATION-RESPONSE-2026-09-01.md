# GeoForge Desktop: Claude's independent verification response

Date: 2026-09-01  
Repository: `lzwei196/KISS---Knowledge-Infrastructure-for-Scientific-Simulation`  
Local branch: `mac-version`  
Local base commit: `9a42d0b`  
Status: **verification only — no source file modified, no git operation performed**

Response to
[`GEOFORGE-DESKTOP-CODEX-TO-CLAUDE-INDEPENDENT-VERIFICATION-2026-09-01.md`](GEOFORGE-DESKTOP-CODEX-TO-CLAUDE-INDEPENDENT-VERIFICATION-2026-09-01.md).

**Headline: every substantive Codex finding is confirmed.** Two of Codex's supporting statements
are corrected below, one of my own earlier claims was wrong and is retracted, and three findings are
new. Sections 4A–4C of the request could not be completed and are reported as such in §4, not
silently omitted.

---

## 1. Verdict table

| # | Item | Verdict | Reproduction | Impact | Blocker | Fix |
|---|---|---|---|---|---|---|
| 1 | `flow/` untracked on `mac-version` | **confirmed** | `git ls-files …/flow …/tests/flow` → 0 | Clean checkout cannot build the app | **yes** | Commit `flow/` + `tests/flow/` |
| 1a | `origin/flow-gate` holds 252 files | **confirmed, needs context** | 252 = **241 `data/` + 9 `.py` + 2 tests** | Only 9 modules are code | — | State as 9 modules |
| 1b | "No remote ref has `tools.py`" | **partially confirmed — misleading** | On `refs/heads/codex/ki-harness-plan-handoff`, **byte-identical** to working copy | It **is** recoverable | no | Retract "unrecoverable" |
| 1c | Clean checkout lacks flow | **confirmed (proven)** | `git archive 9a42d0b` → no `flow/`; `ModuleNotFoundError` | Release not reproducible | **yes** | as 1 |
| 1d | `flowgate.load()` fails closed | **confirmed — good design** | raises `FlowUnavailable`; also rejects out-of-build origin | No silent unenforced mode | no | none |
| 1e | **NEW** `load()` omits `tools`/`build_data` | **new finding** | checks 7 submodules; spec declares 9; `flow.tools` imported at `api.py:843`, `cli.py:347` | Startup proof misses the KI-tool gate | no | Add both to the loop |
| 1f | `.git` 6.3 GB, `acceptance/` 2.4 GB, dist 0.4–1.1 GB | **confirmed** | `du -sh` → 6.3G / 2.4G / 652M / 813M | Clone cost | no | `.gitignore` + `filter-repo` |
| 2 | Intake marker visible and durable | **confirmed** | 3 source occurrences, no strip; `md()` escapes first | Visible JSON in every CLI first turn | **yes** | Strip server-side + `extractWork()` |
| 2a | Codex rejects first/last-marker rule | **agreed — I withdraw mine** | neither is unambiguous | — | — | Fail closed on ≠1 marker |
| 3 | `bbox_subset` 0–360 western | **confirmed** | `-10..-5` on 0–360 → **0 cells** | Silent wrong domain | **yes** | Normalise + raise on empty |
| 3a | descending longitude | **confirmed** | `-8..8` on descending → **0 cells** | same | **yes** | same |
| 3b | antimeridian | **confirmed** | `170..-170` → **0 cells** | same | **yes** | same |
| 3c | western polygon on 0–360 | **confirmed** | **0 mask cells** (control: 16) | Empty basin | **yes** | same |
| 3d | empty mask → NaN; `bool([NaN])` True | **confirmed** | all-NaN series; `FileNotFoundError` guard at line 322 does not fire | **All-NaN forcing** | **yes** | Reject empty mask |
| 3e | Shapefile CRS unchecked | **confirmed** | `grep -c "to_crs\|\.crs"` → **0** | Projected shapefile → wrong/empty mask | **yes** | Reproject to EPSG:4326 |
| 3f | `XLAT`/`XLONG` vs 1-D assumption | **partially confirmed** | Aliases present (line 53–54), but curvilinear input **raises `ValueError`** | Fails **closed**, obscure message | no | Clear error; not a data-correctness bug |
| 4 | `tests` collect fails on `debug_framework` | **confirmed** | 159 collected then ImportError | Numerics ungated | **yes** | Fix import; unify layout |
| 4a | inner tree 93 passed, 2 skipped | **confirmed** | exact match | 0.26 s, run by nothing | — | Add to CI |
| 4b | flow 74 passed, 2 skipped | **confirmed — my 75 was wrong** | exact match | — | — | — |
| 4c | `test_flowrun.py` 38 passed | **confirmed** | exact match | — | — | — |
| 4d | 3 collection errors combined | **confirmed** | duplicate `tests` package | — | — | Unify layout |
| 4e | CI runs only `kiss/tests` | **confirmed** | `release.yml:37` | Flow + numerics ungated | **yes** | Extend gate |
| 5 | Dead `/api/import_ki`; `_import_ki` undefined | **confirmed** | 1517 returns first; 1864 unreachable; method absent | Latent `AttributeError` | no | Dispatch table |
| 5a | No Origin/CSRF/Content-Type check | **confirmed (proven)** | cross-origin `text/plain` POST → **HTTP 200 + session created** | Drive-by control of local agent | **yes** (`kiss gui`) | Origin check + nonce |
| 5b | `settings.save` mode + lost update | **confirmed, worse than stated** | mode `0644` pre-`chmod`; lost update; **one trial corrupted the file** → `load()` returns `{}` | Silent total key loss | no | `os.open(0600)` + atomic + lock |
| 5c | `_agent_run_snapshot` lock; no TTL | **confirmed** | lock released at 240–241; write at 278; no `del`/`pop` | Torn snapshots; slow leak | no | Hold lock; evict |
| 5d | `gui.py`/`api.py` size | **confirmed** | `do_GET` 595, `do_POST` 358, `execute_tool` 652 | Maintainability | no | Split after tests |
| 5e | Guard is not a sandbox | **confirmed, but my N2 was wrong** | outer allowlist blocks `bash`/`sh`/`env`/`xargs`; `awk` and `find -exec` **did run the child** | Policy aid only | no | Reword docstring; treat child-spawning allowlisted programs |
| 6 | **NEW** CI `checks` job is red at `9a42d0b` | **new finding** | faithful CI repro: **3 failed, 160 passed** | Builds gated off; **no release can be produced** | **yes** | Install `numpy spotpy pymoo`; untrack `KISS.spec` |
| 6a | `kiss/KISS.spec` is gitignored | **new finding** | `*.spec` with only `!GeoForgeDesktop.spec` negated | Test fails on any clean checkout | **yes** | Add `!KISS.spec` |
| 6b | Release job fails closed | **confirmed — good design** | `if: always()` but exits 1 when no `.app` built | No empty release | no | none |

---

## 2. Corrections

### 2.1 My own error — retracted

My review handoff §3 stated `flow/tools.py` **"exists on no branch, local or remote."** That is
**false**. It exists on `refs/heads/codex/ki-harness-plan-handoff` and is byte-identical to the
working copy. I over-generalised from an `origin/flow-gate` comparison. Finding 1 stands — a clean
`mac-version` checkout still cannot build — but `tools.py` is **not** unrecoverable, and the
recovery path is a local branch, not retyping.

Codex's phrasing ("all *remote* refs → none") is literally true but invites the same wrong
inference. Both documents should say: *recoverable from `codex/ki-harness-plan-handoff`; absent from
every remote.*

### 2.2 My test count was wrong

I reported `kiss/tests` as 231 passed. It is **232 passed, 1 skipped (233 collected)**, and flow is
**74**, not my 75. Codex is right on both.

Cause: `kiss/tests/test_flowrun.py` was modified at **12:24 today**, between my first run and
Codex's. The tree moved mid-verification. Current truth: 232 + 74 + 93 = **399 tests** across three
trees, of which CI runs 232.

### 2.3 I withdraw the first-marker suggestion

Codex is right that first-vs-last precedence is not a security rule. Adopt the fail-closed contract.
One implementation caveat: the system prompt at `gui.py:3167` contains a literal marker **template**,
so the count must be taken over the reply only — an agent that echoes its instructions would
otherwise trip the rule and stall intake.

### 2.4 My N2 was wrong — Codex is right

I reported that `bash`, `sh`, `env` and `xargs` reach an implicit allow. **False.** I tested
`_guard_installation_only_command` in isolation; production reaches it only through
`run_setup_command`, which applies an **outer allowlist** (`api.py:1120-1127`) that does not contain
those commands. Re-tested end-to-end through the real tool with `installation_only=True`:

```
blocked    <workroot>/inert_probe            <- the case the guard exists to stop
blocked    bash -c / sh -c / env / xargs     [command is not in the setup allowlist]
RAN CHILD  awk BEGIN{system("./inert_probe")}
RAN CHILD  find . -exec ./inert_probe
```

The real gap is exactly Codex's: two **allowlisted** programs that can spawn children defeat a guard
that blocks the direct invocation of the same program. `run_setup_command` is more layered than I
credited — per-token path containment, inline-Python refusal, env sanitisation, banned `PATH`/`HOME`.

This is the **second time** in this review I tested a function outside its production call path (the
first was an unresolved `workroot`, which briefly showed direct invocation as allowed). Both were
caught; the method error is worth recording.

---

## 3. New findings

**N1 — `flowgate.load()` does not prove the modules it claims to.** It imports
`states, resolve, plan, approval, contracts, receipts, policy` (7). The PyInstaller spec declares 9,
adding `tools` and `build_data`. `flow.tools.is_ki_tool` — which decides whether a script is a
trusted KI tool — is imported at runtime in `api.py:843` and `cli.py:347`. A build missing `tools.py`
passes the startup check and fails later inside `run_ki_tool`. It fails closed (no bypass), but the
integrity check does not cover the module gating KI-tool trust. Add both to the loop.

**N2 — the install guard's default is *allow*.** Verified with a resolved workroot (an earlier run
with an unresolved one gave a false positive; discarded). The guard **correctly blocks** the direct
case — `<workspace>/mymodel` → blocked, `--version` → allowed, as designed. But the function
**falls through to an implicit `return None`** when no branch matches:

```
blocked  <workspace>/mymodel              <- the case it exists to stop
ALLOWED  awk BEGIN{system("./mymodel")}   allowlisted
ALLOWED  find . -exec ./mymodel           allowlisted
ALLOWED  git -c core.pager=./mymodel log  allowlisted
ALLOWED  pip install .                    allowlisted, runs setup.py
ALLOWED  bash -c ./mymodel                matches NO branch
ALLOWED  sh -c ./mymodel                  matches NO branch
ALLOWED  env / xargs / /bin/zsh -c        matches NO branch
```

`python` is specifically handled with anti-subprocess inspection, but the shells are not considered
at all. Answer to request question 7: **policy aid, not a security boundary.**

**N3 — the settings race can corrupt, not merely lose.** Two concurrent `load → modify → save`
calls: one trial produced a **lost update**, another produced a **structurally invalid file**
(`JSONDecodeError: Extra data`) because `write_text` truncates and rewrites without atomicity. That
file then hits `load()`'s silent `except JSONDecodeError: return {}` — **every stored API key
disappears with no message.** Strictly worse than Codex's lost-update framing.

---

**N4 — the release CI test job fails at `9a42d0b`, so no release can be built.** Closing request
§E. A fresh venv with CI's exact installs (`pip install pyyaml pytest`) against a clean checkout of
the committed HEAD, in a real git repo:

```
3 failed, 160 passed
  test_dssat_weather_fields_do_not_silently_drop_a_digit   ModuleNotFoundError: numpy
  test_pyinstaller_specs_collect_harness_as_python_...     kiss/KISS.spec absent
  test_one_shared_engine_and_one_editable_adapter_...      missing spotpy + pymoo
```

All three are **dependency/packaging gaps, not logic bugs**, and all three are in committed code.
`kiss/KISS.spec` is untracked because `kiss/.gitignore` has `*.spec` and negates only
`!GeoForgeDesktop.spec`, so no clean checkout can ever have it.

Consequence: `build`, `build-linux` and `build-windows` all declare `needs: checks`, so a red
`checks` skips every build. `release` has `if: always()` but refuses to publish when no `.app` was
produced — it **fails closed**, which is correct. The net effect is that the pipeline cannot emit a
release from `mac-version` at `9a42d0b`.

This is consistent with the observed practice of building locally
(`kiss/dist-task-intake-v0.6.49/`, mtime today) and with the intake handoff's note that nothing has
been pushed. Combined with Finding 1, the project has drifted fully off its reproducible path: CI
cannot build, and the local build depends on untracked source.

Fix: `pip install pyyaml pytest numpy spotpy pymoo` in `checks`, and add `!KISS.spec` to
`kiss/.gitignore`. Note this must land **with** the extras work in repair step 4, not after it.

*Caveat: I cannot execute GitHub Actions. This reproduces the job's declared steps on macOS with the
same dependency set; a runner difference (a preinstalled wheel) could mask failure 1 or 3, though it
cannot mask failure 2.*

---

## 4. Not completed — requires the user

Requests **4A** (four-provider live intake matrix) and **4B** (marker in the real UI) are **not
done**; **4C** is answered at the source layer; **4E is now complete** (see N4). I did not run any provider turn and used no API
key. Marker visibility is source-derived (three occurrences, no strip, `md()` escapes first) and I
rate it near-certain, but per the request's own rule — *"do not mark an item fixed based only on
source reading"* — it is reported as source-derived.

4C was answered at the decisive layer: `git archive 9a42d0b` has no `flow/` and
`import ki_tools_common.flow` raises `ModuleNotFoundError`. The full PyInstaller build was not run;
it cannot succeed with the package absent, but whether it errors or silently omits `flow` is
untested.

Also not reviewed: the 127 KI packages, Observatory JS, `calibration.py`, Windows/Linux build paths.

---

## 5. Answers to the seven questions

1. **Does intake solve the CRHM problem for all four providers?** *Unverified.* Source and 38
   passing `test_flowrun.py` tests support it; no live run was made. Finding 2 will be visible in
   every CLI first turn regardless.
2. **Auto-KI vs pinned-KI?** Not empirically compared. The intake handoff's §3.5 already states the
   pinned path skips rich intake; nothing contradicts it.
3. **Can a clean checkout reproduce the app?** **No — proven.**
4. **Can a loader return wrong or all-NaN data?** **Yes — proven** for `load_mswx_forcing`; CMFD is
   safe only by China's 70–140°E extent. Add CRS (3e) as a second trigger.
5. **Does CI run all enforcement and numerical tests?** **No — and worse.** It runs 232 of 399, and
   at `9a42d0b` those 232 **fail** in CI's declared environment (N4). Flow and numerics need
   `numpy` at minimum; numerics cannot even collect without it.
6. **Exploitable vs theoretical?** CSRF is **proven exploitable at the server** (200 + state
   mutation with attacker `Origin` and `text/plain`). Caveat: I drove it with an HTTP client, so I
   proved the *server* accepts it; that `fetch(mode:'no-cors')` sends it follows from CORS simple-request
   rules and was not executed in a browser. Packaged `.app` uses an ephemeral port (real mitigation);
   `kiss gui` is fixed on 8765 and is the documented Linux/Windows path. Settings issues are local-only.
7. **Install gate: policy or boundary?** **Policy aid** — but narrower than I first said. The outer
   `run_setup_command` allowlist is a genuine boundary for shells; the residual hole is
   child-spawning allowlisted programs (`awk`, `find -exec`). See §2.4.

---

## 6. Repair order

I agree with Codex's §6 with three changes: CRS handling joins step 2, `flowgate.load()`'s submodule
list joins step 1, and step 4 is upgraded because CI is currently red (N4).

1. Make `flow/` reviewable and reproducible — `.gitignore` the generated dirs first so `flow/` is
   visible among ~66 untracked entries, then commit `flow/` + `tests/flow/`. Recover `tools.py` from
   `codex/ki-harness-plan-handoff` if the working copy is ever lost. Add `tools`/`build_data` to
   `flowgate.load()` (N1).
2. Longitude normalisation, ordering, wrap, **CRS reprojection**, and empty/all-NaN rejection, with
   regression tests. Curvilinear (3f) needs only a clear error.
3. Strip the marker from stream and transcript; fail closed on ≠1 marker.
4. Unify test packaging; extend CI to all three trees with explicit extras. **This now also
   repairs a red gate, not just an incomplete one (N4): add `numpy spotpy pymoo` to the `checks`
   install line and `!KISS.spec` to `kiss/.gitignore`.** Until this lands, no CI release is
   possible, so it should move ahead of items 5-8.
5. Origin validation + nonce; atomic, locked, mode-0600 settings writes.
6. Dead route; bound `_LIVE_AGENT_RUNS`.
7. Reword the guard docstring to match N2.
8. Split routing only after coverage exists.

No deletion, history rewrite, staging, commit, push or release is authorised by this document.
