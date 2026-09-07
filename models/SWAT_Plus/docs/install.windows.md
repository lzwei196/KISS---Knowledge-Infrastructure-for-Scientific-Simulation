# SWAT_Plus: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T10:55:10+08:00; 291 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — SWAT+

Reported executable: `<workspace>\binaries\swatplus.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED INSTALLATION on Windows on 2026-09-06: DeepSeek staged a pinned
WinLibs UCRT GCC/gfortran toolchain, built the official source commit above,
produced the self-contained revision 62 PE executable, and reached its SWAT+
startup banner. The curated scientific KI still targets its historical
revision 59.3 project; installation success alone does not assert that an
old TxtInOut case is revision-62 compatible.

On Windows, stage a pinned workspace-local WinLibs UCRT GCC/gfortran release
when no Fortran compiler is on PATH. The pinned source produces the versioned
executable copied to swatplus.exe by this recipe.
A SWAT+ run needs a complete TxtInOut; running the binary in an empty
directory exits immediately and that is not a build failure.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
