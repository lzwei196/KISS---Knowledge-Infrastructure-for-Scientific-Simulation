# CAESAR_Lisflood: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T09:36:18+08:00; 116.6 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — ##################################

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

The upstream Makefile is POSIX-specific and emits bin/hailcaesar. On Windows
the same v1.0 sources can be compiled directly with g++. The portable recipe
deliberately omits -fopenmp when no OpenMP runtime is installed, producing
a scientifically equivalent serial executable instead of blocking setup.

Build the official dvalters/HAIL-CAESAR v1.0 sources. The expected Windows
runtime is bin/HAIL-CAESAR.exe. If a working OpenMP runtime is available you
may add -fopenmp; otherwise use the verified serial command in this manifest.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
