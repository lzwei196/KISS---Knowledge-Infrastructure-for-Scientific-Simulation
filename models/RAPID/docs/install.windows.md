# RAPID installation on Windows

The authoritative Windows setup instructions are in `../kiss.windows.yaml`.
The reproducible route uses the pinned official RAPID commit `83145101`,
PETSc 3.13.6, and a workspace-local portable MSYS2/MinGW toolchain. PETSc
supports native Windows applications built through MSYS2/MinGW:
https://petsc.org/main/install/windows/.

## Installation evidence and limitations

The 2026-09-06 DeepSeek trial built PETSc and the actual RAPID PE executable,
staged its runtime DLL closure, and successfully invoked `--version` and
`--help`. However, it downloaded a moving RAPID main archive and left the
executable in a scratch build directory. The independent installation probe
therefore correctly returned **failed** because the canonical binary was absent.
This is build/startup evidence, not a verified reproducible installation or a
scientific/calibration result. A clean pinned-source revalidation is pending.

## Windows installation lessons

- Use the exact source archives and SHA-256 checksums recorded in the manifest.
- Keep all compiler, source, temporary, cache and output paths in the KI workspace.
- Invoke portable bash with an absolute workspace script path: its login profile
  changes the working directory. Give direct pacman calls their own portable
  `usr/bin` in `env.PATH`, so package hooks find coreutils and certificate tools.
- Build static PETSc with MPIUNI and `--with-proc-filesystem=0`.
- Skip GCC verbose tokens containing `://` in PETSc's old compiler parser to
  avoid accidental UNC library paths and a linker hang.
- Disable PETSc's `OMAKE_PRINTDIR` print-directory option so recursive GNU make
  does not interpret its bare `w` flag as a target.
- Archive PETSc through a response file containing forward-slash relative
  object paths, then run `ranlib`; Windows cannot pass the full object list in
  one native command line.
- Remove only RAPID's optional build-tree convenience symlink. Preserve model
  routing, calibration, I/O and scientific behavior.
- Stage the real executable and its full DLL closure at
  `binaries/RAPID/source/repo/src/rapid.exe` relative to the setup workspace.
  Probe that final path with a restricted runtime PATH.
- Install the manifest Python dependencies in the workspace interpreter and
  record that interpreter in `kiss.toml`.

Do not infer success from Python imports or from a successful scratch build.
The independent installation probe must load the canonical RAPID executable.
