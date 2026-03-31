# Knowledge Dissection Toolkit -- Changelog

## v4.0.0 (2026-03-30) -- "Real Binary, Real Grid, Real Data"

Major release establishing the core methodology for systematic model knowledge
extraction. Driven by the principle that models must run in their original mode
with correctly prepared data.

### Methodology

- **9-stage dissection pipeline** (s0-s8) for processing any Earth science
  model from source code to validated knowledge infrastructure
- **3-step validation protocol**: developer data test, progressive data
  replacement, full autonomous run
- **7 documented anti-patterns** that cause silent failures in model setup
- **Mandatory cal/val temporal split** to prevent data leakage in calibrated
  models

### Shared Utility Library (`ki_tools_common/`)

- 8 modules consolidating patterns found across 435+ model tool scripts:
  - `units.py` -- 40+ named conversion constants, 30+ functions, universal
    `convert()` dispatcher
  - `humidity.py` -- Single canonical Tetens implementation for saturation
    vapour pressure, RH/q conversions, VPD, dewpoint
  - `netcdf_utils.py` -- Coordinate discovery, bounding-box subsetting,
    basin masking, CMFD/MSWX forcing loaders
  - `validation.py` -- Physical range checks with unit-trap heuristics for
    automatic detection of common errors
  - `metrics.py` -- NSE, KGE, PBIAS, RMSE, Pearson r (all NaN-safe), with
    monthly aggregation
  - `io_helpers.py` -- Standard JSON output format, flexible date parsing,
    observation and FLUXNET data readers
  - `forcing_sources.py` -- CMFD/MSWX/ERA5/FLUXNET variable metadata and
    conversion factor lookup
- 45 unit tests covering all critical conversions

### Validators

- `preflight_forcing.py` -- Pre-simulation forcing data checker. Auto-detects
  data source, checks all variables against physical ranges, reports unit-trap
  hints. Catches the most common silent error: unit mismatches.
- `check_calval_split.py` -- Detects data leakage in calibrated models
  (calibrating and validating on the same period).
- `standard_calval.py` -- Standard calibration/validation period helper with
  `split_data()`, `compute_calval_metrics()`, and `calval_objective()` for
  scipy.optimize integration.

### Key Findings (from 97-model synthesis)

- 37% of all errors discovered during dissection are **silent** -- the model
  runs without error but produces scientifically wrong results
- Unit mismatches are the #1 silent error, affecting every model dissected
- The most dangerous specific error: forcing precipitation documented as
  mm/day but stored as kg/m2/s (factor 86400x difference)
- Fixed-width column misalignment is the #2 silent error in Fortran models
- Data leakage (calibrating and validating on the same period) was found in
  5+ models, inflating NSE by approximately 0.10-0.15

---

## v3.0 (2026-03-27)

- Unified dissection pipeline with CLI agent delegation for stages s2-s8
- Domain-specific validation protocols for 15 Earth science domains
- Data registry architecture for institutional dataset management

## v2.0 (2026-03-25)

- Extended methodology beyond hydrology to 15 domains (crop, biogeochemistry,
  lake, flood, groundwater, cryosphere, ocean, etc.)
- Added support for FLUXNET, SNOTEL, and water quality observation datasets

## v1.0 (2026-03-22)

- Initial dissection pipeline for hydrological models
- Standard test basin methodology established
- Validation protocol with three-step progressive replacement
