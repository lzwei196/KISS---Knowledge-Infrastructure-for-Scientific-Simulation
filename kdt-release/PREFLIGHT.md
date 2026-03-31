# Pre-Flight Checklist: Before Dissecting a New Model

**Read this BEFORE starting any model dissection.** It takes 2 minutes and
prevents the errors that took weeks to find across 97 models.

> **Also read `VALIDATION_PROTOCOL.md`** -- it defines the mandatory three-step
> validation process: (1) developer test data, (2) progressive replacement with
> your own data, (3) full autonomous run. A model is NOT validated until Step 3
> passes.

---

## Step 1: Classify Your Model (30 seconds)

Check all that apply -- each triggers specific warnings below:

- [ ] **Has Fortran/C code** -- See [Fortran Traps](#fortran-traps)
- [ ] **Reads fixed-width text files** (not CSV/JSON) -- See [Column Alignment](#column-alignment)
- [ ] **Will be coupled with other models** -- See [Coupling Traps](#coupling-traps)
- [ ] **Has physical units** (m/s, mm/day, W/m2, kg/ha) -- See [Unit Traps](#unit-traps)
- [ ] **Uses spatial data** (lat/lon, shapefiles, rasters) -- See [Spatial Traps](#spatial-traps)
- [ ] **Is a crop/ecosystem model** -- See [Domain Traps](#domain-traps)
- [ ] **Runs on Linux but was built for Windows** -- See [Platform Traps](#platform-traps)
- [ ] **Is a lake/reservoir model** -- See [Lake Model Traps](#lake-model-traps)
- [ ] **Is a 2D flood/inundation model** -- See [Flood Model Traps](#flood-model-traps)
- [ ] **Has a config file separate from the model input** -- See [Config File Traps](#config-file-traps)
- [ ] **Can emulate multiple model structures** -- See [Multi-Structure Traps](#multi-structure-traps)
- [ ] **Has flow routing / drainage network** -- See [Flow Network Traps](#flow-network-traps)
- [ ] **Needs long spinup** (>1 year) -- See [Spinup Requirements](#spinup-requirements)

---

## Step 2: Check the Traps (1 minute)

### Unit Traps (37% of all silent errors come from here)

> **The #1 error across all 97 models. Simulation runs fine. Results are wrong.
> No warning.**

**GOLDEN RULE: NEVER trust data documentation for units. ALWAYS verify by
reading the actual file:**

```python
import xarray as xr
ds = xr.open_dataset('file.nc')
print(ds['prec'].attrs)  # Check 'units' attribute -- this is ground truth
```

**Case Study -- CMFD Unit Correction:** The CMFD (China Meteorological Forcing
Dataset) daily files are documented as mm/day in many places, but the actual
NetCDF attribute says `kg m-2 s-1`. This caused near-zero runoff in multiple
models until caught. The conversion matrix:

| Variable | Actual unit (from NetCDF) | To mm/day | To mm/hr | To m/day |
|----------|--------------------------|-----------|----------|----------|
| prec | **kg/m2/s** | x86400 | x3600 | x86.4 |
| temp | **K** | -273.15 to degC | | |
| pres | **Pa** | /100 to hPa | | |

This pattern is universal: **each model expects DIFFERENT units**, so there is
no single conversion factor:

| Model expects | Conversion from kg/m2/s |
|--------------|------------------------|
| mm/day (most models) | x86400 |
| cm/day | x8640 |
| inches/day | x3401.6 |
| mm/hr | x3600 |
| m/timestep | x3600 x dt_hr / 1000 |
| kg/m2/s native (land surface models) | x1 (no conversion) |
| m/day | x86.4 |

**Real examples of unit errors discovered during dissection:**

| Model | What went wrong | Impact |
|-------|----------------|--------|
| Multiple hydrology models | Precip read as mm/day but is kg/m2/s -- **86400x too low** | Near-zero discharge |
| Lake model | Rain in mm/day instead of **m/day** -- 1000x too much | Lake overflows every day |
| Flood model | Precip in mm/3hr not converted to **mm/hr** | Flood depths 10-100x too high |
| Crop model | Wind m/s vs km/day | ET wrong |
| Soil model | van Genuchten alpha in 1/m not 1/cm (100x) | Infiltration wrong |
| BGC model | Solar radiation in MJ/m2/day not converted to **W/m2** (x11.574) | Cold bias |
| Routing model | mm/timestep not converted to **mm/s** rate | Discharge off by timestep ratio |

### Data Source Selection

> **Not all models should use the same forcing dataset.** Choose based on model
> requirements.

| If model needs... | Consider |
|-------------------|---------|
| Daily forcing (default) | Regional reanalysis at matching resolution |
| Sub-daily timestep | Global sub-daily products (e.g., MSWX 3-hourly) |
| Global coverage | Global reanalysis (ERA5, MSWX) |
| High spatial resolution | Regional high-resolution products |
| Site-level (BGC models) | Eddy-covariance tower data (FLUXNET) |
| Ocean boundary conditions | Ocean reanalysis (HYCOM, GLORYS) |

**Action**: For EVERY input variable, document: (1) what unit the model
expects, (2) what unit your data is in, (3) the conversion factor. Put this
in a table in the skill document.

**Mountain basin check**: If your basin has >500m elevation range AND uses
coarse reanalysis:
- Check: is observed annual runoff > input annual precip? If yes, precip is
  too low (orographic underestimation)
- Consider precipitation scaling: x1.5-2.0 for mountains
- Apply temperature lapse rate: -6.5 degC/km from grid elevation to basin
  elevation
- Consider wind amplification: x3-4 for alpine ridges
- Consider LW radiation correction: -6 W/m2 per 100m elevation gain

### Fortran Traps

| Pattern | What happens |
|---------|-------------|
| Path > 72-256 chars | File not found or reads wrong file -- **silently** |
| Fixed-width column off by 1 | Reads wrong parameter value -- **silently** |
| STOP exits with code 0 | Looks like success but produced no output |
| Resource/error files missing | Crash at startup |
| Needs `--conf` or resources path | Crashes silently without resource directory |

**Action**: `grep 'CHARACTER' *.f*` to find max path lengths. Test with a path
> 80 chars early.

### Column Alignment

> Fortran reads by **column position**, not delimiter. One extra space shifts
> everything.

**Action**: Read the FORMAT statement in the Fortran source. Verify with
`cut -c1-80 < file | head`.

### Coupling Traps

| Pattern | Fix |
|---------|-----|
| **Double-counting** (two models handle same process on same cells) | One model must "own" each process -- mask the other |
| **Temporal mismatch** (different calendar conventions) | Explicitly convert at coupling boundary |
| **Spatial mismatch** (different grid resolutions) | Use area-weighted interpolation, never bilinear for fluxes |
| **Datum mismatch** (different vertical references) | Verify both use same vertical reference |

**Action**: For every coupling, draw a diagram showing: which model handles
which process, what units cross the boundary, and what temporal/spatial
alignment is needed.

### Spatial Traps

| Pattern | What happens |
|---------|-------------|
| CRS mismatch (UTM vs WGS84) | Spatial join returns 0 features -- **silently** |
| Basin shapefile covers wrong area | Entire simulation is for the wrong location |

**Action**: Always `assert gdf1.crs == gdf2.crs` before spatial operations.
Plot the basin on a map before running.

### Domain Traps

| Pattern | Example |
|---------|---------|
| Flag correct for one crop but wrong for another | Legume needs N-fixation flag enabled |
| Model outside valid climate envelope | Tropical crop killed by frost at high latitudes |
| Default planting date wrong for region | Global default DOY vs actual local phenology |
| Abstract species name produces zero output | Some models need specific cultivar/variety codes |

**Action**: When switching crop/region/climate, review ALL model flags. Check
if defaults are universal or context-specific.

### Platform Traps

| Pattern | Example |
|---------|---------|
| Backslash paths | Windows paths in config files fail on Linux |
| Case-sensitive filenames | `SOIL.SOL` vs `soil.sol` -- works on Windows, fails on Linux |
| File encoding | Model expects ISO-8859-1, Python writes UTF-8 by default |
| Line endings | Windows CRLF vs Unix LF may cause parser failures |

**Action**: Test on the target platform early. Check encoding with
`file <filename>`.

### Lake Model Traps

| Pattern | Example |
|---------|---------|
| Rain in mm/day instead of **m/day** | 1000x too much precip -- lake overflows daily |
| Inflow units wrong | Model expects m3/s, upstream model outputs mm/day over grid cell |
| Lake bathymetry inverted | Depth increasing upward vs downward -- different conventions |
| Initial temperature profile wrong | Lake starts isothermal instead of stratified |

**Action**: Triple-check EVERY unit for lake models. They are particularly
sensitive to precipitation and inflow unit errors.

### Flood Model Traps

| Pattern | Example |
|---------|---------|
| DEM resolution too coarse | 0.25 deg DEM for urban flood is meaningless (need <30m) |
| Boundary condition datum mismatch | Water level ASL vs local datum -- flow reversed |
| Manning's n spatially uniform | One value for entire domain misses buildings/vegetation |
| Timestep too large for CFL | Numerical instability |

**Action**: Always validate flood extent against known events before running
scenarios.

### Config File Traps

| Pattern | Example |
|---------|---------|
| Model needs `--conf` or resources path | Crashes silently without it -- no log, no error |
| Config separate from input data | Each file has its own format rules |
| Relative paths in config | Model crashes from wrong working directory |
| Header format determines parsing | Wrong header token causes infinite loop or silent failure |

**Action**: Always run the model's `--help` first. Check if it needs a
config/settings/resources file separate from the project input.

### Multi-Structure Traps

| Pattern | Example |
|---------|---------|
| Invalid physics combination | Some decision combos crash silently |
| Model emulation not exact | Framework emulating Model X is not identical to actual Model X |
| Parameter transfer between structures | Calibrated params for one structure do not work in another |
| "Ignores units" models | Some frameworks do NO unit conversion -- all on you |

**Action**: When using multi-structure frameworks, test one configuration
thoroughly before comparing. Document which physics options were used.

### Flow Network Traps

| Pattern | Example |
|---------|---------|
| D8 cycles on coarse grids | Naive D8 creates cycles in flat terrain -- crash or corruption |
| HRU/cell ID mismatch across files | IDs must match in ALL forcing/param NetCDF files |
| D8 encoding wrong | Different tools use different direction numbering |
| Fortran PARAMETER array too small | Hardcoded dimensions must be recompiled for large domains |

**Action**: Run topological sort on flow network to detect cycles. Verify cell
IDs are consistent across all inputs.

### Spinup Requirements

| Model type | Spinup needed | Why |
|-----------|--------------|-----|
| Biogeochemistry | 1,000-6,000 years | Carbon pool equilibration |
| 3D groundwater | 2-3 years | Water table stabilization |
| Crop models | 1-2 years | Soil moisture initialization |
| Lake models | 1 year | Thermal stratification |
| 3D subsurface | 1-2 years | Pressure head equilibration |

**Action**: Always discard spinup years from performance metrics. Use the
longest recommended spinup for your model family.

---

## The Two Rules

### Rule 1: Copy-First for Control Files

> **NEVER generate model input/control files from scratch. ALWAYS copy from a
> validated example and modify values.**

This is the single most effective error prevention strategy. Legacy Fortran
models have rigid, undocumented input formats that evolved over decades.
Writing files from scratch -- even following the manual -- misses implicit
format requirements (column positions, line ordering, flag-dependent sections,
sentinel values).

**For every new model dissection:**
1. Identify the working example/tutorial files that ship with the model
2. Copy them as templates into the KI package
3. Write tools that **copy the template and update specific values** -- NOT
   tools that generate files from scratch
4. Test the copy-update workflow before attempting any modification

### Rule 2: Check Units First

> **If the model runs without error but the results look wrong, check units
> first.** Unit mismatches are the #1 silent error -- every single model
> dissected had at least one unit trap.

The second most common silent error is fixed-width column misalignment in
Fortran models. The third is header/config format that causes silent parsing
failure.

### Crop-Biogeochemistry Coupling Trap

> If you run a crop model AND a biogeochemistry model on the same grid, they
> MUST be coupled.

The biogeochemistry model's internal crop model is usually uncalibrated and
produces wrong yields. Wrong yields lead to wrong residue, which leads to wrong
greenhouse gas emissions. Use the calibrated crop model to provide residue
inputs to the biogeochemistry model.

---

*Part of the Knowledge Dissection Toolkit by the Jianyun Zhang Research Group,
Hohai University.*
