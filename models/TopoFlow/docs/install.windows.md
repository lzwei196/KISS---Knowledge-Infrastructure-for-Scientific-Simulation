# TopoFlow: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T09:52:39+08:00; 126.1 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (python package) — all declared imports resolve

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows with Python 3.11 on 2026-09-06: the official TopoFlow
repository installed into a clean workspace venv; topoflow,
topoflow.framework.emeli, and the console module all loaded successfully.

TopoFlow is not on PyPI. Install the pinned official GitHub source and its
declared numpy, scipy, netCDF4, and cfunits runtime dependencies into the
workspace Python environment.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
