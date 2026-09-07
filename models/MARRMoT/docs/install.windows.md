# MARRMoT on Windows

The Windows runtime is GNU Octave with the MARRMoT MATLAB source toolbox.
The executable installation contract is the real `octave-cli.exe`, with
the complete Octave distribution, the pinned MARRMoT source and loaded
`optim`/`statistics` packages. Python dependencies support the KI wrappers.

## Reproducible inputs

- [GNU Octave official portable distribution](https://octave.org/download):
  `https://ftp.gnu.org/gnu/octave/windows/octave-11.3.0-w64.7z`,
  481,127,074 bytes; SHA-256
  `fd3cf0e885467a15211b8ceded42800432a5462481324d49a896ef257e05d1a0`.
- [MARRMoT v2.1.2 source](https://github.com/wknoben/MARRMoT/tree/a95b925669385e6c747637dec45c848601177ea4),
  commit `a95b925669385e6c747637dec45c848601177ea4`.
- Extract the archive into `binaries/MARRMoT/octave/`, retaining its
  `octave-11.3.0-w64` top-level directory. Clone the source into
  `binaries/MARRMoT/source/repo/`.

The [official Windows notes](https://wiki.octave.org/Octave_for_Microsoft_Windows)
describe the portable archive and package registration. If `pkg list` does
not show the bundled packages, `pkg rebuild -global` registers the packages
inside this portable installation. Then load `optim` and `statistics`.
No system installer, administrator action, MATLAB license, or observation
dataset is needed for this route.

## Windows pitfalls corrected in the KI

- `/usr/bin/octave` was a Linux-specific path. The wrapper and preflight now
  find the portable runtime from the nearest `kiss.toml` binaries directory,
  with `OCTAVE_EXECUTABLE` and ordinary PATH as alternatives.
- Source discovery now uses the same managed prefix and verifies the real
  `MARRMoT_model.m` sentinel. `--marrmot-path` or `MARRMOT_PATH` remains
  available for independently installed copies.
- Generated Octave scripts normalize Windows separators and double embedded
  single quotes, including in the forward, Monte Carlo and CMA-ES paths.
- A failing Octave startup no longer masquerades as a successful function
  probe. Calibration forcing and parameter files are optional in software
  preflight because those are project inputs.
- The minimal v2.1.2 model constructor leaves `solver_opts` empty. Set
  `resnorm_tolerance=0.1` and `resnorm_maxiter=6` before `get_output()`;
  otherwise the upstream solver reports `matrix cannot be indexed with .`.
  The KI wrapper already sets these; the included smoke script now does too.

## Validation record

2026-09-07: fresh DeepSeek setup at `D:\gmarr1` returned **installed/ready in
302.0 seconds**. GeoForge resolved the canonical real PE executable, which
reported GNU Octave 11.3.0. DeepSeek installed NumPy, pandas, xarray and
matplotlib in a dedicated venv and recorded its interpreter in `kiss.toml`.
The official archive size and SHA-256 were independently checked. The test
saved `D:\gmarr1\results.jsonl` and automatically removed the install tree.

The setup-agent interface permits only help/version startup probes in
installation-only mode. Its result therefore does not itself claim model
execution. An independent load probe succeeded before cleanup: `optim` and
`statistics` loaded, and `m_01_collie1_1p_1s` instantiated with one store and
one parameter.

A separate fresh extraction at `D:\gmarrverify` then ran the checked-in
`tools/windows_smoke.m` against the same pinned source and verified ten
synthetic daily timesteps. It printed:

```text
MARRMOT_SMOKE_OK octave=11.3.0 timesteps=10
sumQ=28.311125005 sumEa=18.391216634 finalS=89.297658360
waterBalance=-1.42108547152e-14
```

All ten discharge values and final stores were finite; discharge and actual
evapotranspiration were nonnegative. Input precipitation totalled 136 mm.
The real Python KI wrapper independently produced matching outputs from a
forcing/output directory containing an apostrophe (`O'Brien`), confirming
Windows path quoting end to end. Three focused Python regression tests and
Python compilation checks passed. This is a synthetic numerical smoke test,
not a calibrated or observed watershed validation.
