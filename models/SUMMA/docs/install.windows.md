# SUMMA: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T13:44:06+08:00; 990.9 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — ----------------------------------------------------------------------

Reported executable: `<workspace>\binaries\summa\bin\summa.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

The pinned official v3.0.0 source matches this KI's
SUMMA_FILE_MANAGER_V3.0.0 configuration era. A clean Windows installation
stress run built and launched the native v3.0.0 executable; scientific
reference-case verification remains pending.

Do not derive a branch from the descriptive KI version string. Build the
pinned official v3.0.0 source above. On Windows, stage a workspace-local
WinLibs UCRT gfortran/make toolchain. Do not request MSYS2, a POSIX shell, or
a human toolchain choice: a prior clean Windows stress run already built the
compatible netCDF libraries and compiled SUMMA to its final link using native
CMake, mingw32-make and gfortran. Patch the few POSIX-only make recipes in the
workspace copy or issue their equivalent native commands. Build compatible
zlib, HDF5, netCDF-C, netCDF-Fortran and BLAS/LAPACK libraries inside the same
workspace when no development SDK is available, then supply F_MASTER, FC,
FC_EXE, INCLUDES and LIBRARIES to build/Makefile. Use exactly zlib 1.3.1,
HDF5 1.14.2, netCDF-C 4.9.2 and netCDF-Fortran 4.6.1 for this Windows build;
this is the dependency chain already observed compiling through netCDF-C.
Do not downgrade any of these versions and do not delete upstream feature or
minimum-version checks to force an older dependency through configuration.
Avoid conda or micromamba compiler environments: use the standalone WinLibs
UCRT toolchain directly so MinGW startup objects and runtime libraries stay
coherent. WinLibs x86_64 UCRT GCC/gfortran 14.3.0 with Ninja and CMake 4.0.2
completed the full native build. In particular, do not use HDF5 1.14.4 with
GCC 16, whose
`_Float16` probe enables conversion code that
then fails because the MinGW headers do not define `FLT16_MAX`. Configure
HDF5 with `CMAKE_C_FLAGS=-D_GNU_SOURCE`: its CMake probe can find
`vasprintf` under MinGW-UCRT while the actual library build cannot see the
declaration without that feature macro. Build the HDF5 high-level library
(`HDF5_BUILD_HL_LIB=ON`) because netCDF-4 uses its dimension-scale API. Also
pass `BUILD_TESTING=OFF` (not only `HDF5_BUILD_TESTING=OFF`) so HDF5's
POSIX-only test framework does not fail on the missing `alarm` function after
the required libraries compile. If the usual release URLs fail, the tested
official sources are `https://zlib.net/fossils/zlib-1.3.1.tar.gz` and
`https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.2/src/hdf5-1.14.2.tar.gz`.
Keep the short build and install prefixes when reconfiguring rather than
restarting with a different SDK. With the pinned netCDF-C 4.9.2 on
MinGW-UCRT, patch
only the workspace source in `libdispatch/dpathmgr.c` so the buffers passed
to `_stat64` and `_wstat64` are cast to `struct _stat64 *`; the unpatched
code passes `struct stat *` and does not compile. Build the `netcdf` library
target and use `cmake --install build` after it links. Configure netCDF-C
with `BUILD_UTILITIES=OFF` (not the unused `ENABLE_UTILITIES` spelling),
`ENABLE_BYTERANGE=OFF`, `ENABLE_DAP2=OFF`, `ENABLE_DAP4=OFF`,
`ENABLE_HDF5_ROS3=OFF`, `ENABLE_S3=OFF` and `ENABLE_NCZARR=OFF`; these
CURL-dependent features and the `ncgen`/`ncdump` utilities are not required
by SUMMA. Pass `ZLIB_LIBRARY` and `ZLIB_INCLUDE_DIR` as absolute paths with
forward slashes: CMake 4 on Windows otherwise inserts a path such as
`D:\\...` into netCDF-C's `try_compile` source and rejects `\\g` as an invalid
escape. When configuring netCDF-Fortran, put the netCDF-C, HDF5
and zlib install prefixes in `CMAKE_PREFIX_PATH`, their `lib` directories in
`CMAKE_LIBRARY_PATH`, and their DLL directories on the setup-command PATH.
If its CMake check claims netCDF-C 4.7.4 or newer is required, inspect
`CMakeFiles/CMakeConfigureLog.yaml`: in the observed MinGW run
`nc_def_var_szip` was present in `libnetcdf.dll`, but the check link failed
because it could not find `-lhdf5_hl-shared` and `-lhdf5-shared`. Do not
rebuild the stack with SZIP unless the symbol is actually absent; first make
the already-built HDF5 import libraries visible to the linker. If the
generated `p/lib/cmake/netCDF/netCDFTargets.cmake` exports those nonexistent
`*-shared` names, replace its `INTERFACE_LINK_LIBRARIES` with absolute
workspace paths to `p/lib/libhdf5_hl.dll.a` and `p/lib/libhdf5.dll.a`, then
clear the cached failed CMake symbol probes (or use a new build directory)
before reconfiguring the pinned netCDF-Fortran 4.6.1. Treat that link error
as an exported-target naming problem, not as permission to fall back to
netCDF-Fortran 4.5.x or netCDF-C 4.7.x.
For MinGW, netCDF-Fortran's C shim uses
dllimport symbols: build netCDF-C as a DLL, link the final model against
`libnetcdff.dll.a` followed by `libnetcdf.dll.a` (not only static archives), and
copy `libnetcdf.dll` plus required MinGW runtime DLLs beside summa.exe. This
exact chain completed with netCDF-Fortran 4.6.1 and Reference-LAPACK 3.12.0.
SUMMA v3.0.0's Makefile contains POSIX-only version, cleanup and install
recipes. If no allowed POSIX shell is available, mirror its existing compile
groups with native gfortran in this exact order: noah-mp; common
NRUTIL/NRPROC/hookup/dshare/UTILMS; netcdf; PRELIM; MODRUN; SOLVER; DRIVER.
The DATAMS files such as `multiconst.f90` and `globalData.f90` are under
`build/source/dshare`, not `engine`. Generate `summaversion.inc`, add its
containing directory with `-I` when compiling DRIVER, and use a GCC response
file for the object list at final link to avoid Windows command-length and
wildcard-expansion problems. Link `-lnetcdff -lnetcdf -llapack -lblas`, then
copy the netCDF/HDF5/zlib and MinGW runtime DLLs beside `bin/summa.exe`.
A clean stress run verified the standalone result with `--help` and
`--version` (`v3.0.0`) in 990.9 seconds. This
dependency build and native makefile port are already authorized; continue
rather than asking the user merely because they are large or a shell command
from the upstream recipe needs a Windows equivalent.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
