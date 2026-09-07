# HYPE: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T13:19:18+08:00; 742.1 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — ran — still working after 25s (--version)

Reported executable: `<workspace>\binaries\HYPE\HYPE.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows on 2026-09-06: the official SMHI HYPE 5.35.0
executable archive was checksum-verified, extracted, and the PE loaded its
Fortran main routine and printed the HYPE 5.35.0 banner. HYPE treats normal
help/version flags as a run-directory argument, so its bounded startup probe
is expected to keep working until GeoForge's probe timeout.

Download the official release archive from the pinned SourceForge file URL;
the SourceForge project page is not a Git repository and must not be cloned.
Use the shipped HYPE.exe rather than rebuilding merely to prove installation.
Do not pass a demo/run directory in installation-only mode. The executable
does not implement --help or --version: a bounded probe that loads the PE and
reaches its HYPE 5.35.0 startup banner is sufficient; missing scientific run
inputs are not an installation failure. Install every declared Python import
in the same recorded workspace interpreter.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
