> **MANDATORY EXECUTION POLICY** — READ BEFORE PROCEEDING
>
> You MUST run the **actual model binary or package** described in this document.
> If the model fails to import, compile, or execute, you MUST:
> 1. Check `diagnostics/triplets.yaml` for a matching error pattern
> 2. Try the fix suggested in the triplet's `remedy` section
> 3. If still failing, report the error to the user with full details
>
> You MUST NOT substitute a simplified Python formula, regression equation,
> or hand-coded approximation in place of the real model. Doing so produces
> scientifically invalid results and defeats the purpose of the KI.
>
> Before starting, run: `python preflight_check.py` (in this KI directory)
> to verify that the model binary/package and required data are available.

---

# SWAT+ Knowledge Infrastructure — Agent Entry Point

**Model**: SWAT+ (Soil and Water Assessment Tool Plus)
**Developer**: USDA-ARS / Texas A&M AgriLife Research
**Version**: Rev 60.5+ (Fortran CLI, modular text-based inputs)
**Domain**: Watershed hydrology, water quality (nitrogen, phosphorus, sediment)
**Repository**: https://github.com/swat-model/swatplus
**Documentation**: https://swatplus.gitbook.io/io-docs

---

## What This Infrastructure Enables

Autonomous operation of SWAT+ for watershed-scale simulation of:
- **Hydrology**: Surface runoff (SCS CN method), lateral flow, groundwater recharge/return flow, channel routing, ET, snowmelt
- **Water Quality**: Nitrogen cycle (5 pools: NO3, NH4, active/stable organic N, fresh organic N), phosphorus cycle (6 pools), sediment yield (MUSLE)
- **Land Management**: Crop growth, tillage, fertilizer application, irrigation, pesticide fate

SWAT+ is the successor to SWAT2012 with key architectural differences:
- **No ArcGIS dependency** — all inputs are modular text files in a TxtInOut folder
- **Flexible spatial connectivity** — any object can route to any other object (not forced subbasin hierarchy)
- **file.cio master control** — single file lists all input files by category
- **calibration.cal** — text-based parameter adjustment without editing individual files

---

## Pipeline Overview (9 Stages)

| Stage | Name | Key Tools | Skill Document |
|-------|------|-----------|----------------|
| S1 | Watershed Delineation | `delineate_watershed`, `define_subbasins` | `docs/s1_watershed_delineation_skill.md` |
| S2 | HRU Definition | `create_hru_overlay`, `apply_hru_threshold` | `docs/s2_hru_definition_skill.md` |
| S3 | Weather Data Preparation | `prepare_weather_files`, `generate_weather_stations`, `validate_weather_data` | `docs/s3_weather_preparation_skill.md` |
| S4 | Soil Database | `build_soils_database`, `validate_soil_properties` | `docs/s4_soil_database_skill.md` |
| S5 | Land Use & Management | `build_management_schedules`, `configure_landuse` | `docs/s5_landuse_management_skill.md` |
| S6 | Calibration Parameters | `generate_calibration_file`, `apply_calibration` | `docs/s6_calibration_parameters_skill.md` |
| S7 | Simulation Configuration | `configure_file_cio`, `configure_time_sim`, `configure_print_prt`, `validate_txtinout` | `docs/s7_simulation_config_skill.md` |
| S8 | Model Execution | `compile_swatplus`, `run_swatplus` | `docs/s8_model_execution_skill.md` |
| S9 | Output Parsing & Analysis | `parse_channel_output`, `parse_basin_output`, `compute_performance_metrics`, `check_mass_balance` | `docs/s9_output_parsing_skill.md` |

**Dependency graph**: S1 -> S2 -> S5; S1 -> S3; S4 (independent); S2+S4 -> S6; S1-S6 -> S7 -> S8 -> S9

---

## Tools Reference

| Stage | Tool ID | Script Path | Purpose |
|-------|---------|-------------|---------|
| S1 | `delineate_watershed` | `tools/s1/delineate_watershed.py` | DEM processing to subbasins + stream network |
| S1 | `define_subbasins` | `tools/s1/define_subbasins.py` | Generate subbasin connectivity files |
| S2 | `create_hru_overlay` | `tools/s2/create_hru_overlay.py` | Overlay landuse/soil/slope to create HRUs |
| S2 | `apply_hru_threshold` | `tools/s2/apply_hru_threshold.py` | Filter small HRUs below area thresholds |
| S3 | `prepare_weather_files` | `tools/s3/prepare_weather_files.py` | Convert forcing data to SWAT+ .pcp/.tmp/.slr/.hmd/.wnd format |
| S3 | `generate_weather_stations` | `tools/s3/generate_weather_stations.py` | Create weather-sta.cli and wgn.wgn |
| S3 | `validate_weather_data` | `tools/s3/validate_weather_data.py` | QC weather files for physical consistency |
| S4 | `build_soils_database` | `tools/s4/build_soils_database.py` | Generate soils.sol from HWSD/SSURGO/SoilGrids |
| S4 | `validate_soil_properties` | `tools/s4/validate_soil_properties.py` | Validate soil physical consistency |
| S5 | `build_management_schedules` | `tools/s5/build_management_schedules.py` | Generate management.sch operation sequences |
| S5 | `configure_landuse` | `tools/s5/configure_landuse.py` | Generate landuse.lum lookup table |
| S6 | `generate_calibration_file` | `tools/s6/generate_calibration_file.py` | Create calibration.cal parameter file |
| S6 | `apply_calibration` | `tools/s6/apply_calibration.py` | Validate calibration parameters |
| S7 | `configure_file_cio` | `tools/s7/configure_file_cio.py` | Generate/update file.cio master control |
| S7 | `configure_time_sim` | `tools/s7/configure_time_sim.py` | Set simulation period and warmup |
| S7 | `configure_print_prt` | `tools/s7/configure_print_prt.py` | Configure output printing options |
| S7 | `validate_txtinout` | `tools/s7/validate_txtinout.py` | Cross-check all file references |
| S8 | `compile_swatplus` | `tools/s8/compile_swatplus.py` | Compile SWAT+ Fortran source with CMake |
| S8 | `run_swatplus` | `tools/s8/run_swatplus.py` | Execute SWAT+ binary |
| S9 | `parse_channel_output` | `tools/s9/parse_channel_output.py` | Parse channel_sd discharge/sediment/nutrients |
| S9 | `parse_basin_output` | `tools/s9/parse_basin_output.py` | Parse basin-level water/nutrient balance |
| S9 | `compute_performance_metrics` | `tools/s9/compute_performance_metrics.py` | Compute NSE, PBIAS, KGE, RMSE |
| S9 | `check_mass_balance` | `tools/s9/check_mass_balance.py` | Verify water/nutrient mass balance closure |

---

## Critical Domain Knowledge

### 1. TxtInOut Is the Working Directory
SWAT+ reads file.cio from the current working directory. You MUST `cd` into TxtInOut before running the binary. All paths in file.cio are relative to TxtInOut.

### 2. file.cio Category Order Matters
The file.cio categories must appear in the exact order expected by SWAT+. Do not rearrange lines. Use 'null' for unused optional categories — do not delete the line.

### 3. Weather File Format Is Strict
Each .pcp/.tmp/.slr/.hmd/.wnd file has a 3-line header:
- Line 1: Title/comment (free text)
- Line 2: Column headers (variable names)
- Line 3: Station metadata (name, nbyr, tstep, lat, lon, elev)
- Line 4+: Data rows (year, jday, value(s))

Files are space-delimited. Missing data must be -99.0 (not NaN or blank).

### 4. soils.sol Has Multi-Line Records
Unlike most SWAT+ files (one line per record), soils.sol uses 2-10 lines per soil:
- Line 1: Profile-level properties (SNAM, HYDGRP, SOL_ZMX, ANION_EXCL, SOL_CRK, TEXTURE)
- Lines 2-N: Per-layer properties (SOL_Z, SOL_BD, SOL_AWC, SOL_K, SOL_CBN, CLAY, SILT, SAND, ROCK, SOL_ALB, USLE_K, SOL_EC, SOL_CAL, SOL_PH)
The number of layer lines must match the number of soil layers. Mismatch causes silent wrong results.

### 5. Calibration.cal Uses Three Change Types
- `absval`: Set parameter to this exact value (replaces)
- `abschg`: Add this value to current parameter (shift)
- `pctchg`: Change by this percentage (multiply by 1 + value/100)

For spatially variable parameters (CN2, AWC, SOL_K), use `pctchg` to preserve spatial heterogeneity. Using `absval` overwrites all HRUs to the same value.

### 6. Warmup Period Is Essential
SWAT+ needs 2-3 years of warmup for soil moisture, groundwater, and nutrient pool initialization. Set `nyskip` in time.sim. Output during warmup years should be excluded from performance evaluation.

### 7. HRU Threshold Affects Mass Balance
Aggressive HRU thresholds (>20%) remove significant land area. The removed area is redistributed to dominant HRUs, which can bias water yield and nutrient loads. Typical safe thresholds: 5-10% for land use, 5-10% for soil, 10-20% for slope.

### 8. Key Calibration Parameters (Hydrology)
| Parameter | Range | Controls | Change Type |
|-----------|-------|----------|-------------|
| cn2 | 25-98 | Surface runoff generation | pctchg |
| esco | 0-1 | Soil evaporation depth | absval |
| awc | -50 to +50% | Soil water holding | pctchg |
| surlag | 0.05-24 | Surface runoff lag | absval |
| lat_ttime | 0-180 | Lateral flow travel time (days) | absval |
| canmx | 0-100 | Canopy interception (mm) | absval |
| epco | 0-1 | Plant ET compensation | absval |
| perco | 0-1 | Percolation coefficient | absval |
| alpha_bf | 0-1 | Baseflow recession constant | absval |
| gw_delay | 0-500 | Groundwater delay (days) | absval |
| revap_co | 0.02-0.2 | Groundwater revap coefficient | absval |
| flo_min | 0-5000 | Minimum flow to shallow aquifer (mm) | absval |

---

## Error Handling

Diagnostic triplets are in `diagnostics/triplets.yaml`. Key failure patterns:

- **dt_001**: file.cio references missing file -> fatal, file not found in TxtInOut
- **dt_002**: Weather file format error -> fatal, wrong header line count or missing columns
- **dt_003**: Temperature Tmax < Tmin -> silent error, ET and snowmelt wrong
- **dt_004**: HRU threshold too aggressive -> silent, biased water yield
- **dt_005**: Fortran array bounds exceeded -> fatal, segfault or STOP
- **dt_008**: Wrong watershed delineation (outlet on wrong stream) -> silent, wrong basin area
- **dt_010**: Nutrient mass balance not closed -> silent, wrong water quality results
- **dt_012**: Solar radiation units wrong (MJ/m2 vs W/m2) -> silent, wrong ET

---

## SWAT+ vs VIC Comparison

| Aspect | SWAT+ | VIC |
|--------|-------|-----|
| Spatial unit | HRU (landuse+soil+slope) | Grid cell (lat/lon) |
| Routing | Internal channel routing | External (Lohmann or CaMa-Flood) |
| Water quality | Full N/P/sediment | Hydrology only |
| Calibration | calibration.cal text file | Edit soil parameter file |
| Management | Tillage, fertilizer, irrigation | None |
| Input format | Text files in TxtInOut folder | Text files + global param |
| Typical use | Agricultural water quality | Regional/continental hydrology |

---

## Coupling with HydroCraft

SWAT+ can use the same data sources as VIC:
- **DEM**: Same basin delineation tools (WhiteboxTools)
- **Forcing**: CMFD/MSWX converted to SWAT+ weather files via `prepare_weather_files`
- **Soil**: HWSD global raster shared with VIC soil parameters
- **Observed data**: Same GRDC/HYDAT station data for validation

See `docs/model_couplings.yaml` for detailed coupling specifications.

---

*This knowledge infrastructure was built using the Knowledge Dissection Toolkit v1.0 (Jianyun Zhang Research Group, Hohai University).*
