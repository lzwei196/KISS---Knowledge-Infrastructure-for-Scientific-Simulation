# FSM2: Windows installation experience

This record is specific to Windows. Preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-07T19:36:26+08:00; 177 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow.
The complete test ran from a fresh workspace; it was not a manual GUI click-through.

Reported executable: `<workspace>\binaries\FSM2\source\repo\FSM2.exe`.
GeoForge's independent PE probe reached the official namelist reader at
`FSM2_PARAMS.F90:128`, returning `Fortran runtime error: End of file` when
stdin was empty. FSM2 reads a namelist from stdin and has no version/help
command-line interface, so this EOF establishes that the executable loaded.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the pinned source,
toolchain, build order, executable contract, and runtime DLL instructions.
The same recipe is retained in the legacy shared manifest for older GeoForge versions.

- Official source: [RichardEssery/FSM2](https://github.com/RichardEssery/FSM2),
  commit `f0c86be12274354c958c2b71661cefefd6ae79f3` (v2.1.2 bug fix).
- Private compiler: WinLibs UCRT gfortran 16.2.0,
  archive SHA-256 `9714f9e55905000ec2a066ae033abdfe8c93083a925e3fe015d3c7cc4bb1c918`.
  The setup agent verified the archive hash before extraction.
- Build the ASCII configuration from the upstream `compil.sh` (`PROFNC=0`),
  using its exact module-first source order with native gfortran.
  This route requires neither NetCDF nor a POSIX shell. All compiler files
  remain in the setup workspace.
- Keep `libgfortran-5.dll`, `libquadmath-0.dll`, `libgcc_s_seh-1.dll`, and
  `libwinpthread-1.dll` beside the executable. Startup works without the
  compiler's PATH.
- The test created a private Python 3.13.5 venv, installed numpy 2.5.3 and
  pandas 3.0.5, and recorded its `Scripts/python.exe` as `kiss.python`.
  Both imports and `pip check` passed.

The KI wrapper formerly expected `src/FSM2` after compilation, but Windows
gfortran emits `FSM2.exe`. The wrapper now builds and moves the native
platform filename and resolves it for `--run-only`. Preflight resolves the
configured binaries source tree and its `.exe`, while retaining the legacy
source-tree and suffix-free POSIX executable paths.

## Independent official example execution

After compilation, a separate check copied the real PE and its runtime DLLs
away from the installation tree and ran the unchanged official
`nlst_Alptal.txt` with `met_Alptal_0405.txt`. This is the upstream example for
the winter of 2004-2005 at Alptal, Switzerland, with one open and one forested
point. It completed with exit code 0, using all 5,832 forcing records.

| Output | Rows | Columns | Check |
|---|---:|---:|---|
| `Alptal_flux.txt` | 5,832 | 18 | All values finite |
| `Alptal_stat.txt` | 5,832 | 22 | All values finite |
| `Alptal_subc.txt` | 5,832 | 12 | All values finite |

The DS-produced executable SHA-256 was
`04a91b18900eb48b6d62703b5f5d7e34510007816f58e5373f4e25752e1ef910`.
The source and algorithm were not modified for this run. The installation
test and the scientific example were separate checks; installation-only
setup itself did not run a simulation.

This proves successful installation and execution of the official sample,
including finite, structurally complete outputs. It does not establish
agreement with observations, successful calibration, or support for the
optional NetCDF output build. The dedicated installation was cleaned after
its result was recorded.
