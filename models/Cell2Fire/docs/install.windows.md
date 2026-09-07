# Cell2Fire: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T09:46:52+08:00; 69.7 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — version: v1.0.1

Reported executable: `<workspace>\binaries\Cell2Fire\source\repo\Cell2Fire\Cell2Fire.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

Windows installation observed during the 2026-09-06 DeepSeek stress test.
Upstream's v1.0.1 Windows release contains Cell2Fire.exe together with its
jpeg62, liblzma, TIFF, and zlib runtime DLLs. Boost and libtiff development
packages are needed only when compiling from source and must not block the
official prebuilt Windows installation.

Prefer the official fire2a/C2F-W v1.0.1 Windows x86_64 release. Keep the EXE
and all DLLs from the archive together. A valid Windows result is
Cell2Fire.exe in this KI's managed source/repo/Cell2Fire directory; probe it
by absolute path because the Windows launcher may not resolve a nested
relative executable.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
