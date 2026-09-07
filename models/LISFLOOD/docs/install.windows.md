# LISFLOOD: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T13:00:46+08:00; 446.9 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (python package) — all declared imports resolve

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

Official LISFLOOD-OS v5.0.0. Upstream documents Python >=3.10,<3.13 and
installs the mandatory PCRaster/GDAL native runtime from conda-forge. The
The full declared import set passed the fresh Windows installation check on 2026-09-06.

Stage the official standalone micromamba Windows executable inside the
workspace. Use explicit workspace-local `--root-prefix` and `--prefix`
arguments to create a Python 3.11 environment and install `pcraster` and
`gdal` plus `numpy<2.3` and the declared Python imports from conda-forge; this
is already authorized and must not be handed to
the user as a Miniconda permission request. Windows hosts may have
LongPathsEnabled=0: use exactly the shortest workspace-top-level prefixes
`r` (root), `e` (environment), and `p` (`CONDA_PKGS_DIRS`), and confirm the
selected paths with `micromamba info`. This workspace-local cache workaround
must be tried before requesting a registry change or shorter workspace.
Invoke that environment's Python
directly (do not use `micromamba run`) to pip-install the pinned
`lisflood-model==5.0.0` package and every declared import. The official
sdist assumes POSIX `gdal-config` and a development-checkout VERSION layout.
On Windows, patch the unpacked official source before building its wheel:
obtain GDAL metadata from the already-installed environment `osgeo` package,
and let `lisflood/__init__.py` also resolve `sys.prefix/VERSION`. Do not edit
the installed site-packages copy. These are packaging/layout fixes only.
`--no-deps` is
acceptable only after all upstream constraints are already satisfied in that
interpreter; finish with `python -m pip check`, then record the environment
interpreter in kiss.toml.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
