# CE_QUAL_W2: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T10:11:04+08:00; 252.8 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — ran — still working after 25s (--version)

Reported executable: `<workspace>\binaries\ce_qual_w2\bin\w2_v5.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows on 2026-09-06: the official ERDC v4.5 Windows executable
loaded successfully and wrote W2CodeCompilerVersion.opt identifying
CE-QUAL-W2 Version 4.50, Intel compiler 2021, build date 2022-04-26. The
executable has no terminating help/version flag, so a bounded startup probe
is expected to time out after proving that it loaded.

Use the official precompiled Windows model executable shipped in the pinned
ERDC repository. Preserve the full checkout for documentation and support
files, but do not copy it into a second nested source tree.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
