# RHESSys: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **installed** (2026-09-06T14:10:33+08:00; 384.1 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: runnable (pe) — FATAL ERROR: in construct_command_line option #1 is invalid.

Reported executable: `<workspace>\binaries\RHESSys\source\repo\rhessys\rhessys7.4.exe`.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

Windows recipe pinned to the official RHESSys-7.4 tag. A fresh installation
compiled the generated flex/bison parser and netCDF-linked PE model and
passed the independent startup check on 2026-09-06.

Do not derive a branch name from the descriptive KI version string. Use the
pinned official RHESSys-7.4 commit above and do not switch to trunk/develop
when a portability error occurs. A complete Windows build has already passed
with the following route, so execute it directly; do not spend the turn
researching other compilers, parsing GitHub release JSON, inventing a
multi-source GCC driver, translating generators, or designing a replacement
build system. Download WinLibs from
`https://github.com/brechtsanders/winlibs_mingw/releases/download/13.3.0posix-11.0.1-ucrt-r1/winlibs-x86_64-posix-seh-gcc-13.3.0-mingw-w64ucrt-11.0.1-r1.7z`
and extract it with the official `https://www.7-zip.org/a/7zr.exe`; download
`https://github.com/lexxmark/winflexbison/releases/download/v2.5.25/win_flex_bison-2.5.25.zip`.
Clone the pinned source directly at the canonical
`binaries/RHESSys/source/repo` tree, stage/extract micromamba correctly,
install `libnetcdf`, generate the import library and parser, run the upstream
dynamic-field source generator, patch the existing makefile minimally, build
its object whitelist, link, stage DLLs, and probe. The setup runner explicitly
permits the pinned upstream `bin/dynamic_field_lookup.py` command as source
generation; execute it directly and never request user permission for it.
Use two ordinary tar calls (create an archive from the complete conda
`Library/bin` directory, then extract it beside `rhessys7.4.exe`) to stage
runtime DLLs without shell pipes or globs. Compile exactly the source/object whitelist
in that pinned commit's upstream makefile; do not wildcard every historical
`.c` variant. Page a long makefile with read_work_file start_line/line_count
rather than reconstructing or guessing the list. On Windows, stage a
workspace-local WinLibs UCRT GCC 13.x toolchain (13.3.0 or the pinned
13.2.0 release), not an unpinned latest GCC 14+ archive: newer compilers turn
several legacy pointer diagnostics into hard errors and invite unsafe model
source edits. Also stage the portable `lexxmark/winflexbison` v2.5.25
release (Bison 3.8.2 and Flex 2.6.4). Invoke
WinLibs' `mingw32-make.exe` and staged `win_flex.exe`/`win_bison.exe`
directly by workspace path. Do not install MSYS2, invoke pacman, or request a
human-operated POSIX console: a prior clean Windows stress run already
generated the parsers and compiled all 335 RHESSys model objects with these
native tools, so absence of bash/pacman is not a valid blocker. Patch only the
workspace makefile's POSIX shell/path syntax when required, or issue the
equivalent native generator/compiler/link commands, without changing model
code or scientific defaults. Pass the
workspace tool directories in env.PATH on every call because env overrides
are not persistent. Running win_flex.exe/win_bison.exe on the upstream .l/.y
inputs is an allowed compilation step. The upstream makefile must also
generate `util/index_struct_fields.c` with
`bin/dynamic_field_lookup.py`. If a direct Python command is conservatively
rejected in installation-only mode, replace that makefile recipe's
`python3` token with the absolute workspace-venv Python path and let
`mingw32-make.exe` invoke it as the declared source-generation dependency;
that nested build step is allowed and was validated in a clean Windows
build. Do not omit `index_struct_fields.o` or hand-write a surrogate. Compile
the generated Bison parser
and Flex lexer explicitly with `-std=c99`: current WinLibs GCC defaults to
GNU C23 when the upstream `CFLAGS_NO_C99` rule is used, where `bool` is a
keyword and conflicts with RHESSys' ABI-significant `typedef short bool`.
Preserve that upstream 16-bit boolean definition; do not replace it globally
with `<stdbool.h>` merely to make the parser compile. A native MinGW link can
expose exactly two non-scientific POSIX portability gaps: `strndup` from the
UCRT C library and Flex's `yywrap`.
Resolve them in one separately compiled Windows compatibility object that
implements normal POSIX `strndup` allocation/copy/NUL-termination semantics
and returns 1 from `yywrap`; do not edit RHESSys model routines, boolean
storage, algorithms, parameters, or defaults to address either symbol. For
the netCDF C dependency, prefer
staging micromamba in the workspace and installing conda-forge's real
Windows `libnetcdf` package into a shallow prefix such as `p/nc` (keep the
micromamba root/package cache at shallow workspace paths too). The official
`https://micro.mamba.pm/api/micromamba/win-64/latest` response is a
`.tar.bz2` package, not a raw executable: save it as an archive and extract
the real `Library/bin/micromamba.exe`; never rename the archive to `.exe`,
which can hang Windows process creation. Use that
package's `Library/include` headers and `Library/bin/netcdf.dll`, retain its
adjacent runtime DLLs beside the final executable, and do not substitute a
Python extension module or a hand-written symbol-stub library. Generate a
genuine MinGW import library from the staged netcdf DLL with WinLibs'
`gendef.exe` and `dlltool.exe` when no compatible `.dll.a` is supplied, then
link the complete upstream RHESSys object whitelist against it. The MinGW
link command must name the output explicitly as `-o rhessys7.4.exe` (not
`-o rhessys7.4`: because that version-like suffix suppresses MinGW's usual
automatic `.exe` addition). Produce the Windows artifact as
`rhessys/rhessys7.4.exe`; keep it and all required DLLs
in the same source-tree directory so GeoForge can copy that complete tree to
the canonical `binaries/RHESSys/source/repo/rhessys/` location before its
independent probe. Record the
exact conda package/version and keep its licence metadata. If this binary
package route is incompatible, build official
netCDF-C classic-only with source kept anywhere but CMake build/install dirs
placed at the shallow workspace paths `b/nc` and `p/nc`; disable HDF5, DAP,
utilities and tests. Continue without requesting separate permission for
that normal dependency build, native makefile port, or path-length workaround.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
