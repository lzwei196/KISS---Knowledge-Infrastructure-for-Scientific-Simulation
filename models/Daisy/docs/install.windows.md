# Daisy: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T09:37:58+08:00; 217.3 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — Daisy crop/soil simulation version 7.1.14. (Aug 31 2026)

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

The KI was authored against an untagged 7.1.4 development build. Upstream
currently publishes the same 7.1 line as v7.1.14, including a self-contained
Windows archive with daisy-bin.exe, runtime DLLs, libraries, samples, and its
embedded Python. DeepSeek installed and started this exact archive during the
2026-09-06 Windows stress test; scientific verification remains separate.

Prefer the checksum-pinned official v7.1.14 Windows archive. Keep the whole
extracted directory together because daisy-bin.exe needs its adjacent DLLs,
lib directory, and embedded Python runtime. Probe with daisy-bin.exe -v.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
