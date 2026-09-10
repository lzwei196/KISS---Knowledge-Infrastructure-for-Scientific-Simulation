# GeoForge Desktop — Linux build

Linux is built from `kiss/KISS.spec` (one-file, browser UI — pywebview's Linux
backend can't be frozen, so the app opens the default browser).

## Where the code comes from

This `linux-version` branch is based on `mac-version`, because that branch's
install-and-verify code is written cross-platform: it branches on
`platform.system()` and picks the ELF/Linux paths on their own. Basing Linux
on it — rather than on lean `main` — is what gives the Linux build the same
KI-install hardening the macOS and Windows builds have:

- `runnable.py` verifies binary, Python, R, Octave, Julia and Python-script
  model KIs (the language modules `rpackage.py`, `octpackage.py`,
  `jpackage.py`, `python_script.py`, `native_probe.py`).
- hardened `install.py`, `install_locations.py`, `setup.py`.

`main` deliberately stays lean and does not carry this; per-OS install is
per-OS by nature.

## Verified on Linux (2026-09-10)

Frozen build from `KISS.spec`, this box:

- `list` → 127 of 127 packages, self-contained
- `harness-status` → ready, contract 3,932 chars
- all five language modules present in the frozen binary (checked via the PYZ)
- install/verify batteries: `test_octave_package`, `test_r_package`,
  `test_julia_package`, `test_install_integrity`, `test_native_runtime_assets`
  → 31 passed, 68 subtests
- `test_runtime.py` → 149 passed, 1 failed

## Known deltas (not fixed here)

1. `test_runtime.py::ProviderHealthTests::test_missing_alias_and_duplicate_workdir_are_not_passed_to_cli`
   fails: with the sandbox mocked off, an extra dir such as `/mnt/disk3` is
   still passed to the CLI as `--add-dir` when the test expects it dropped.
   Inherited verbatim from `mac-version` (this branch has zero code diff from
   it), in the ProviderHealth area already flagged as fragile. Left for the
   owner of that code; it is not introduced by the Linux adaptation.

2. Windows-version's `_started_before_missing_input` runnability heuristic is
   not ported. It is self-contained but its call site sits inside a
   `runnable.py` that diverges from mac's by ~800 lines, so weaving it in by
   hand risks correctness for one edge case. Port deliberately if wanted.
