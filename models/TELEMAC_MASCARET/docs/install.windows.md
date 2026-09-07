# TELEMAC_MASCARET: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T14:38:15+08:00; 295.6 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — 2D VERSION 9.1 FORTRAN 2003

Reported executable: `<workspace>\binaries\TELEMAC_MASCARET\b\bin\telemac2d.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

The project website is not a Git remote. The official v9.1.0 source is commit
a040e817390e787c5395be95663381ae85a4c0e3 in the pam-retd GitLab repository.
Its checkout contains roughly 1,500 Git LFS data objects that are not needed
to compile the serial TELEMAC-2D core and can make a Windows setup appear to
hang while Git LFS downloads them.

Build the real official serial TELEMAC-2D executable; a Python wrapper or a
Python import is not the model product. Clone
`https://gitlab.pam-retd.fr/otm/telemac-mascaret.git` directly into the
configured binaries role at `binaries/TELEMAC_MASCARET`. Never run a plain
`git clone`: it starts Git LFS and invalidates this bounded install. Clone
with `git clone --filter=blob:none --no-checkout <repo>
binaries/TELEMAC_MASCARET`, passing `GIT_LFS_SKIP_SMUDGE=1`,
`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=Never`, and bounded Git low-speed
timeouts through the command's `env` object. Pass `GIT_LFS_SKIP_SMUDGE=1`
again when checking out exact commit
`a040e817390e787c5395be95663381ae85a4c0e3`. Do not clone the project website
and do not fetch Git LFS data during installation-only setup. Keep source and
build paths short; configure the official CMake tree with a short build
directory named `b` so the canonical product is
`binaries/TELEMAC_MASCARET/b/bin/telemac2d.exe`. Stage a pinned WinLibs UCRT
GCC/gfortran toolchain entirely inside the workspace; do not install or alter
a system compiler. A tested toolchain is WinLibs 16.2.0 posix-seh UCRT
`https://github.com/brechtsanders/winlibs_mingw/releases/download/16.2.0posix-14.0.0-ucrt-r1/winlibs-x86_64-posix-seh-gcc-16.2.0-mingw-w64ucrt-14.0.0-r1.7z`,
SHA-256
`9714f9e55905000ec2a066ae033abdfe8c93083a925e3fe015d3c7cc4bb1c918`.
Use that toolchain's gfortran, gcc, and Ninja with CMake, add
`-fallow-argument-mismatch -std=legacy`, and explicitly disable MPI, MED,
MUMPS, AED2, GOTM, TelApy, the HERMES wrapper, and documentation; MPI and
METIS are optional and are not required for the serial core. Before
configuring, make one exact build-system-only portability fix in the
workspace checkout at `sources/utils/parallel/CMakeLists.txt`: immediately
after `add_library(parallel SHARED ${parallel_sources})`, add
`target_link_libraries(parallel PUBLIC special)` and remove `special` from
the existing MPI-only `target_link_libraries` line, leaving
`target_link_libraries(parallel PUBLIC MPI::MPI_Fortran)`. Do not modify
scientific source or algorithms. Build target `homere_telemac2d`, whose
Windows output name is `telemac2d.exe`. Preserve every TELEMAC DLL generated
in `b/bin`. Inspect the executable and generated DLLs with the staged
`objdump.exe`, then copy their complete non-system WinLibs runtime closure
beside the executable (normally `libgfortran-5.dll`, `libquadmath-0.dll`,
`libgcc_s_seh-1.dll`, and `libwinpthread-1.dll`); the final probe does not
inherit the compiler PATH. The independent installation probe must launch
the PE long enough to observe the official `2D VERSION 9.1 FORTRAN 2003`
startup banner. A later missing CONFIG/T2DDICO error is acceptable evidence
that the genuine core loaded; do not fetch LFS examples, run a tutorial, or
run KI preflight during installation-only testing. Install all declared
Python dependencies into one recorded interpreter and require `pip check`
plus imports, but never treat that Python layer as a substitute for the core
PE.

## Additional evidence or limitation

The executable printed the official 2D VERSION 9.1 FORTRAN 2003 banner before missing CONFIG/T2DDICO input. No scientific case was run. This test reused host Python; a pre-existing unrelated pftools/PyYAML pip-check conflict remained.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
