# OpenHydroQual: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **needs-user** (2026-09-06T13:24:49+08:00; 275.7 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: OpenHydroQual cannot be compiled on this machine yet because Qt6 is a hard, unconditional dependency of the engine source and I have no compatible Qt kit or MSVC toolchain.

EVIDENCE (verified, not assumed):
- aquifolium/include/Utilities.h includes <QJsonArray> unconditionally; System.h uses Qt types under Q_JSON_SUPPORT/QT_GUI_SUPPORT, both set by the official build.
- Real g++ -fsyntax-only of aquifolium/src/Object.cpp fails immediately: "QJsonArray: No such file or directory".
- The repo's own BUILD.md declares the Windows route as MSVC 2019/2022 + Qt6-for-MSVC + vcpkg GSL. There is no official Qt-free engine build.
- Installed toolchain here is only tdm64-gcc (MinGW) 10.3.0 + cmake + git; no MSVC, no Qt, no GSL, no qmake. The git 'libs/lapack-blas_lib_win64' LAPACK/BLAS folder is not tracked in the repo, and the jsoncpp submodule content is not checked out either.

Both supported Windows paths end at the same point I cannot cross in-workspace: the Qt/Visual-Studio installer requires an account login / licence, and MSVC is a system-wide install that also needs a licence.

How should I proceed?
Choose an installation route for the missing Qt6 + C++ toolchain, or supply a prebuilt artifact / archive. The official OHQ source is already staged under <workspace>\src (tags v2.0.4 and master/2.0.7).

Reported executable: `<workspace>\binaries\OpenHydroQual\source\repo\OHQLibTest\OHQLibTest.exe`.

This is an unresolved attempt, not proof that Windows cannot support the model. A missing dependency or executable path still needs diagnosis before assigning a user action.

Last agent request category: `licence`.
OpenHydroQual Windows build needs a compatible Qt6 + C++ toolchain
OpenHydroQual cannot be compiled on this machine yet because Qt6 is a hard, unconditional dependency of the engine source and I have no compatible Qt kit or MSVC toolchain.

EVIDENCE (verified, not assumed):
- aquifolium/include/Utilities.h includes <QJsonArray> unconditionally; System.h uses Qt types under Q_JSON_SUPPORT/QT_GUI_SUPPORT, both set by the official build.
- Real g++ -fsyntax-only of aquifolium/src/Object.cpp fails immediately: "QJsonArray: No such file or directory".
- The repo's own BUILD.md declares the Windows route as MSVC 2019/2022 + Qt6-for-MSVC + vcpkg GSL. There is no official Qt-free engine build.
- Installed toolchain here is only tdm64-gcc (MinGW) 10.3.0 + cmake + git; no MSVC, no Qt, no GSL, no qmake. The git 'libs/lapack-blas_lib_win64' LAPACK/BLAS folder is not tracked in the repo, and the jsoncpp submodule content is not checked out either.

Both supported Windows paths end at the same point I cannot cross in-workspace: the Qt/Visual-Studio installer requires an account login / licence, and MSVC is a system-wide install that also needs a licence.

How should I proceed?
Choose an installation route for the missing Qt6 + C++ toolchain, or supply a prebuilt artifact / archive. The official OHQ source is already staged under <workspace>\src (tags v2.0.4 and master/2.0.7).

## Next installation

Read this KI's SKILL.md, diagnostics and upstream installation documentation. No reviewed Windows-specific recipe has been embedded yet. Reproduce the real software and record its source revision, local dependencies, executable path and independent check before promoting a new recipe to observed.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
