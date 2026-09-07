# Alpine3D: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T14:25:49+08:00; 92.8 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — <workspace>\binaries\Alpine3D\source\repo\Source\alpine3d\bin\alpine3d.exe 3.20 compiled on Sep  7 2020 22:05:00

Reported executable: `<workspace>\binaries\Alpine3D\source\repo\Source\alpine3d\bin\alpine3d.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

OBSERVED on Windows on 2026-09-06 from the official WSL/SLF GitLab generic
package. The 3.2.0 x64 executable loaded its adjacent official Alpine3D,
Snowpack, MeteoIO and MinGW runtime DLLs and printed Alpine3D 3.20 help.
No scientific inputs are required for this installation probe.

On Windows, deploy the official prebuilt WSL/SLF package; do not spend time
rebuilding its MeteoIO and Snowpack dependency stack. The exact package is
`https://gitlabext.wsl.ch/api/v4/projects/11/packages/generic/alpine3d/3.2.0/Alpine3d-3.2.0-x86_64.exe`
with SHA-256
`300c211c79aee15e8d823308c202e09745125e3ff619a52ef82586fdfa7dd13e`.
This file is an NSIS installer containing the real model and DLLs; it is not
itself the Alpine3D model executable, and must never be copied or renamed to
satisfy `produces`. Avoid executing it because its embedded manifest asks
for administrator access. Extract it entirely inside the setup workspace.
Bootstrap full 7-Zip without installing it: download official
`https://www.7-zip.org/a/7zr.exe` (SHA-256
`ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d`)
and `https://www.7-zip.org/a/7z2603-x64.exe` (SHA-256
`0859c524b8a63551848f0c246abddcb1d0b7b656b0fbfe879f8d85e61a9e6edd`).
Use 7zr to extract the full 7-Zip package into a workspace tools directory,
then use that extracted `7z.exe` plus its adjacent `7z.dll` to extract the
Alpine3D NSIS package. Every `produces` path below is relative to the
install prefix `binaries/Alpine3D/`, not the setup-workspace root. Extract
the package root directly into
`binaries/Alpine3D/source/repo/Source/alpine3d/`, preserving its complete `bin`, `doc`,
`include`, and licence tree. The final model must be exactly
`source/repo/Source/alpine3d/bin/alpine3d.exe`, with `libalpine3d.dll`,
`libsnowpack.dll`, `libmeteoio.dll`, `libgcc_s_seh-1.dll`,
`libstdc++-6.dll`, and `libwinpthread-1.dll` adjacent. Probe that exact
executable with `--help`; valid output begins with its Alpine3D 3.20,
Libsnowpack 3.60 and MeteoIO 2.90 versions and includes `Usage:`. Do not use
Python, a wrapper, a launcher, the installer executable, or another KI's
binary as the reported artifact. Scientific forcing and project data are
user inputs and are not required for installation.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
