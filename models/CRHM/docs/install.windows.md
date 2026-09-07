# CRHM: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-05T20:51:07+08:00; 243 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — Unrecognized option "--version" given. Use option --help for usage information.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

Native Windows build observed on 2026-09-05. A shallow CMake build directory
is required on hosts where the legacy MAX_PATH limit breaks spdlog's nested
ExternalProject compiler probe.

Clone the official crhmcode source and initialise its spdlog submodule. On
Windows configure in a shallow directory such as workspace/bld, then place
the resulting crhm.exe at binaries/crhm/bin/crhm.exe. The help command exits
1 by design after printing usage; printed usage proves startup.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
