# DSSAT: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T10:35:38+08:00; 274.1 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — -----------------------------------------------------------------------------

Reported executable: `<workspace>\binaries\DSSAT\build\bin\dscsm048.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows on 2026-09-06: DeepSeek staged a workspace-local WinLibs
UCRT GCC/gfortran release, cloned the official v4.8.5.41 commit above,
configured an out-of-source Ninja RELEASE build, linked the self-contained
build/bin/dscsm048.exe, and reached the real DSSAT command-line usage screen.
This tag already contains the two FORMAT corrections formerly patched by
the macOS v4.8.5.0 recipe.

DSSAT requires an out-of-source CMake build. The executable is
build/bin/dscsm048.exe and must retain access to the checkout's Data directory.
On Windows, use a pinned workspace-local WinLibs UCRT GCC/gfortran toolchain
and preserve the compiler runtime DLLs when no system gfortran is available.
Model-specific weather, soil, genotype, and management inputs are prepared
later for each simulation; they are not installation prerequisites.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
