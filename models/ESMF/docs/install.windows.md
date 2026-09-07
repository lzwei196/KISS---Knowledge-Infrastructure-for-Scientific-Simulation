# ESMF: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T14:45:29+08:00; 243.8 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — ESMF_VERSION_STRING:       8.4.0

Reported executable: `<workspace>\binaries\ESMF\env\Library\bin\ESMF_RegridWeightGen.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows on 2026-09-06 with the official conda-forge
ESMF/ESMPy 8.4.0 nompi pairing. The real PE utilities reported ESMF 8.4.0,
ESMF_PrintInfo and esmf.mk reported linked NetCDF support, and ESMPy
initialised its native core for a 2-by-2 Grid/Field write/read operation.
GeoForge's independent final check resolved the canonical PE product and
returned installed/ready. A bare or shimmed Python import is not a valid
installation. Newer ESMF releases do not currently have official
conda-forge win-64 packages.

On Windows use the last official conda-forge native pairing; do not attempt
to compile current ESMF with an improvised MSVC/MinGW mixture and do not
create a placeholder `esmpy` module. Bootstrap workspace-local micromamba
from `https://micro.mamba.pm/api/micromamba/win-64/latest`. That response is
a `.tar.bz2` conda package, not an executable: extract the actual
`Library/bin/micromamba.exe` before running it. Keep its root/package cache
at a short workspace path. Create the environment exactly at
`binaries/ESMF/env` with conda-forge only and no user rc, installing exact
`esmpy=8.4.0=nompi_py311h597d70b_2`, `esmf=8.4.0=nompi_h693c31f_5`,
`netCDF4`, and `python=3.11`. Record
`binaries/ESMF/env/python.exe` as `[kiss].python` in `kiss.toml`. The ESMPy
package build SHA-256 is
`ec6f50bca562123bfea26a46016024913d61e5678cf4c4414d3ee88840ecb6e4`.
The final product must be the real PE executable at the manifest's exact
relative path `env/Library/bin/ESMF_RegridWeightGen.exe`, accompanied by
`ESMF_PrintInfo.exe`, `Library/lib/esmf.dll`,
`Library/lib/esmf_fullylinked.dll`, and `Library/lib/esmf.mk`; never copy or
rename Python, a shell script, or a launcher to satisfy `produces`. A direct
micromamba create command must pass the fully resolved absolute environment
prefix to `-p`, never the relative text `binaries/ESMF/env`; otherwise conda
writes relative library locations into `esmf.mk`. Verify `ESMF_LIBSDIR` and
`ESMF_NETCDF_LIBPATH` in the installed `esmf.mk` resolve to this environment.
A direct
process invocation needs normal conda activation variables. For an explicit
manual probe, set `ESMFMKFILE` to
`binaries/ESMF/env/Library/lib/esmf.mk` and prepend the environment root,
`Library/mingw-w64/bin`, `Library/usr/bin`, `Library/bin`, `Library/lib`,
`Scripts`, and `bin` to PATH, or use the extracted micromamba's `run -p`
command. Require
both probes: `ESMF_PrintInfo.exe` must report ESMF 8.4.0 and NetCDF support;
environment Python must import NumPy and ESMPy, initialise
`esmpy.Manager(debug=False)`, create a 2-by-2 `esmpy.Grid` using a NumPy
int32 max_index, attach an `esmpy.Field`, assign four values and read their
correct sum. Scientific coupling inputs are user data and are not required
for this installation probe.

## Additional evidence or limitation

An additional independent native ESMPy check created a Manager, 2×2 Grid and Field and obtained sum=28.0. This is a core-operation smoke test, not a geoscientific validation or calibration.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
