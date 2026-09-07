# SWAP: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T10:26:59+08:00; 146.1 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — running swap ....

Reported executable: `<workspace>\binaries\SWAP\swap.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows on 2026-09-06: the official SWAP v4.2.0 MinGW release
asset matched its GitHub release SHA-256, had a valid PE header, and loaded
through the installation runtime probe. Project inputs are prepared later.

Install the official Windows x64 release asset. Do not require a Fortran
compiler when this published binary is available.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
