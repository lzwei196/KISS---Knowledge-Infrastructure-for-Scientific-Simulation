# SimFire: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T13:30:56+08:00; 436.1 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (python package) — all declared imports resolve

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

The official 2.0.1 source requires Python >=3.9,<3.10 and its noise 1.2.2
dependency has no CPython 3.9 Windows wheel. Windows installation therefore
needs a private Python 3.9 runtime plus a real native build of noise.

FIRST clone the pinned official SimFire source into this workspace and apply
the Windows patch below before installing SimFire; do not install an
unpatched SimFire wheel and do not try to repair the installed copy afterward.
The exact source is
`git+https://github.com/mitrefireline/simfire.git@5d76a16de45e7058e5080f2cf4c5b5b2f9f1d0ae`;
check out that commit even if you cloned the default branch first. Use the
pinned official source, not a nonexistent PyPI `simfire` release.
Use CPython 3.9 only. Poetry's `~3.9` constraint here means >=3.9,<3.10,
not <4.0; an actual Windows attempt with Python 3.11 was rejected by upstream
with `Package 'simfire' requires a different Python: 3.11.0 not in
'<3.10,>=3.9'`. Do not spend time trying Python 3.11 or 3.13. Stage official
CPython 3.9.13 from the official NuGet `python` package inside the workspace
(`https://api.nuget.org/v3-flatcontainer/python/3.9.13/python.3.9.13.nupkg`).
That archive already contains the matching `tools/include` headers and
`tools/libs` import libraries; use those real SDK files rather than
synthesising a Python import library or downloading unrelated headers.
Then build noise 1.2.2's _simplex and _perlin extensions with a pinned
workspace-local compiler. Invoke staged gcc.exe with the required CPython
include/library arguments; GeoForge permits those compiler payloads. Do not
use an unrelated compiler already on the host for the final build. Do not
hand-assemble a noise wheel, write dist-info metadata, directly copy modules
into site-packages, or create a replacement setup.py. Preserve noise's real
packaging by using its official setup.py. CPython 3.9's workspace-staged
`Lib/distutils/cygwinccompiler.py` predates UCRT-era MSVC numbers; apply the
standard workspace-local build-tool fix so `get_msvcr()` returns an empty
runtime-library list for MSC versions >=1900, and run setuptools with
`SETUPTOOLS_USE_DISTUTILS=stdlib`. If the staged GCC reports C inline-linkage
errors, patch the official noise setup.py Windows compile arguments to add
`-fgnu89-inline`. Then run the staged Python with noise's official
`setup.py build --compiler=mingw32 bdist_wheel` and install the generated
platform wheel with pip. Do not finish with a curated `--no-deps` subset:
install every upstream-declared SimFire runtime dependency within its
version bounds plus the KI imports below, and require `python -m pip check`
to report no broken requirements. Pin `setuptools==80.9.0` in this Python
3.9 environment: newer setuptools releases remove the `pkg_resources`
module that SimFire 2.0.1 imports at startup. Keep
all portability changes explicit and do not replace model algorithms or
scientific dependencies with placeholder modules; do not rewrite or shim
the POSIX-only `wurlitzer` package itself. SimFire imports
`wurlitzer.pipes` only to silence optional non-headless sprite-render output,
but importing wurlitzer raises ModuleNotFoundError for the POSIX-only `fcntl`
module on native Windows. Apply this approved portability patch to the
workspace copy of
`simfire/game/sprites.py`: when `os.name == "nt"`, bind `pipes` to
`contextlib.nullcontext`; on every other platform retain
`from wurlitzer import pipes`. This edits SimFire's optional output-capture
call site, not wurlitzer, and does not change fire-model algorithms or
scientific dependencies. Do not create an `fcntl.py`, wurlitzer substitute,
`.pth` hook, or any other compatibility module in site-packages; direct
site-packages edits are forbidden. Build and install a wheel from that patched pinned
source. Installing the real wurlitzer dependency is fine, but the patched
SimFire source must not import it on Windows. Then point `kiss.python` at the
Python 3.9 environment and verify the real `simfire.sim.simulation` import.
Install the KI's declared
rasterio, xarray, geopandas and requests imports into that same Python 3.9
environment even when they are not direct dependencies of the simfire wheel.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
