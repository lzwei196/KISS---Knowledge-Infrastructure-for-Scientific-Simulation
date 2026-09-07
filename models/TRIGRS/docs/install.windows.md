# TRIGRS: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T14:07:29+08:00; 162 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — TRIGRS: Transient Rainfall Infiltration

Reported executable: `<workspace>\binaries\TRIGRS\src\TRIGRS\trg.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

The official USGS GitLab archive is publicly cloneable at
code.usgs.gov/usgs/landslides-trigrs. The older
code.usgs.gov/ghsc/lhp/trigrs path triggers an authentication flow and can
leave git-remote-https and Git Credential Manager processes waiting forever
on Windows. The v2.1.0 source layout is src/TRIGRS, not the historical
source/trigrs_full/src/TRIGRS layout.

On Windows, clone only the current official repository
`https://code.usgs.gov/usgs/landslides-trigrs.git` and check out exact commit
`969c409f7bc63e7616ebe34dfd5f6afd967f2d2d`. Do not use the obsolete
`/ghsc/lhp/trigrs` URL. Make git non-interactive with
`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=Never`, an empty credential helper,
and a bounded low-speed timeout so a server/authentication failure cannot
leave credential-manager children running. Clone the repository directly
into the configured binaries role at `binaries/TRIGRS`, not into a generic
workspace `src` directory: GeoForge resolves the product at
`binaries/TRIGRS/src/TRIGRS/trg.exe`. Stage a pinned WinLibs UCRT
GCC/gfortran toolchain entirely inside the setup workspace; do not use the
unrelated host TDM GCC, and do not install a system compiler. A tested
archive is WinLibs 16.2.0 posix-seh UCRT
`https://github.com/brechtsanders/winlibs_mingw/releases/download/16.2.0posix-14.0.0-ucrt-r1/winlibs-x86_64-posix-seh-gcc-16.2.0-mingw-w64ucrt-14.0.0-r1.7z`, SHA-256
`9714f9e55905000ec2a066ae033abdfe8c93083a925e3fe015d3c7cc4bb1c918`;
Windows bsdtar can extract that archive. Build only the official serial
`trg` target. The upstream Makefile uses `MPIF90` even in its suffix rules
for serial objects, so override `F90`, `FC`, and `MPIF90` with the staged
gfortran, set `F90FLAGS=-w -O3 -std=legacy -fallow-argument-mismatch`, and
override the optional GSL link flags with `CCFLAGS=-lm`. MPI and GSL are not
required for the serial executable. Use the staged `mingw32-make.exe`; the
expected Windows product is `binaries/TRIGRS/src/TRIGRS/trg.exe`. Use the
staged `objdump.exe` to inspect its imported DLLs, then copy every non-system
WinLibs runtime it needs (normally `libgfortran-5.dll`, `libquadmath-0.dll`,
`libgcc_s_seh-1.dll`, and `libwinpthread-1.dll`) from the staged toolchain
beside `trg.exe`; the final probe does not inherit the compiler PATH.
Preserve the checkout and its sample input files alongside the executable. Installation-only testing
may run the executable just long enough to observe its TRIGRS startup banner,
but must not run a tutorial simulation or preflight.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
