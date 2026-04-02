# S9: Output Parsing and Evaluation

## Purpose

Parse, interpret, and validate DSSAT-CSM output files to assess simulation quality, diagnose simulation failures, and extract key results for reporting and calibration workflows.

## Prerequisites

- [ ] S8 (Batch Execution) completed: the model has been run and output files exist in the working directory.
- [ ] You know which treatments were simulated (from the batch file or run log).
- [ ] If evaluating against observed data: measured values are available for comparison (yield, phenology, etc.).
- [ ] You understand the crop being simulated and its expected phenology and yield range.

## Inputs

| Parameter          | Type       | Source              | Description                                         |
|--------------------|------------|---------------------|-----------------------------------------------------|
| Working directory  | Path       | S8 output           | Directory containing all `.OUT` files               |
| Treatment list     | Integers   | Batch file          | Which treatments to evaluate                        |
| Measured data      | Table      | Experiment records  | Observed yield, phenology, biomass for comparison   |
| Crop type          | CHAR*2     | FileX               | Crop code (MZ, WH, SB, etc.) for range checks      |

## Procedure

### Step 1: Verify Output File Inventory

#### Step 1.1: List Expected Output Files

After a successful DSSAT run, the following files should exist in the working directory:

| File             | Content                                  | When Created                     | Critical? |
|------------------|------------------------------------------|----------------------------------|-----------|
| Summary.OUT      | One-line-per-treatment seasonal summary  | After SEASEND (phase 6)          | Yes       |
| Overview.OUT     | Formatted multi-section summary          | After SEASEND (phase 6)          | Yes       |
| Evaluate.OUT     | Simulated vs measured comparison         | After SEASEND if IDETO='Y' or 'E'| Conditional|
| PlantGro.OUT     | Daily plant growth variables             | Daily during OUTPUT (phase 5)    | Yes       |
| SoilWat.OUT      | Daily soil water by layer                | Daily during OUTPUT (phase 5)    | Yes       |
| SoilTemp.OUT     | Daily soil temperature by layer          | Daily during OUTPUT (phase 5)    | Optional  |
| Nitrogen.OUT     | Daily nitrogen dynamics                  | Daily during OUTPUT (phase 5)    | Conditional|
| GHG.OUT          | Daily greenhouse gas emissions           | Daily during OUTPUT (phase 5)    | Optional  |
| MgmtEvent.OUT    | Log of applied management operations     | When operations are applied      | Yes       |
| WARNING.OUT      | Non-fatal warning messages               | When warnings occur              | Check     |
| ERROR.OUT        | Runtime error messages                   | When errors occur                | Check     |
| MODEL.ERR        | Error code descriptions (reference file) | Installed with executable        | Reference |
| RunList.OUT      | List of simulations executed             | After RUNINIT (phase 1)          | Optional  |
| EnvSum.OUT       | Environmental summary by growth phase    | After SEASEND (phase 6)          | Optional  |

#### Step 1.2: Check for Missing Files

```bash
ls -la Summary.OUT Overview.OUT PlantGro.OUT SoilWat.OUT MgmtEvent.OUT
```

- If `Summary.OUT` is missing: the model either did not start or crashed before SEASEND. Check ERROR.OUT and WARNING.OUT.
- If `PlantGro.OUT` is missing: the model crashed before the first OUTPUT phase, or IDETG='N' (growth output suppressed) in simulation controls.
- If `Evaluate.OUT` is missing: IDETO is not set to 'Y' or 'E', or no measured data (T-file) exists for comparison.

#### Step 1.3: Check for Error Files

```bash
# Check if ERROR.OUT exists and has content
if [ -f ERROR.OUT ]; then
    echo "ERRORS DETECTED:"
    cat ERROR.OUT
fi

# Check WARNING.OUT
if [ -f WARNING.OUT ]; then
    echo "WARNINGS:"
    cat WARNING.OUT
fi
```

If ERROR.OUT exists, the simulation encountered fatal errors. The ERRKEY and ERRNUM in the file can be cross-referenced with MODEL.ERR for detailed descriptions.

---

### Step 2: Parse Summary.OUT

#### Step 2.1: Understand Summary.OUT Structure

Summary.OUT contains one header section and one data line per simulated treatment-season. This is the primary file for extracting yield, phenology, and water balance results.

Source reference: Variables are defined in the `SummaryType` data construct (`OPSUM.for` lines 38-91) and written during SEASEND.

#### Step 2.2: Key Variables and Units

The following table lists the most important variables. All dates are in YYDDD format. All -99 values mean "not computed" or "not available."

**Phenology and Dates:**

| Variable | Units  | Description                                | Typical Range        |
|----------|--------|--------------------------------------------|----------------------|
| PDAT     | YYDDD  | Planting date                              | Matches FileX PDATE  |
| EDAT     | YYDDD  | Emergence date                             | PDAT + 3-15 days     |
| ADAT     | YYDDD  | Anthesis (flowering) date                  | PDAT + 40-90 days*   |
| MDAT     | YYDDD  | Physiological maturity date                | ADAT + 20-70 days*   |

*Ranges are crop-dependent. Maize: ADAT = PDAT + 50-75d, MDAT = ADAT + 30-55d. Wheat: ADAT = PDAT + 60-120d, MDAT = ADAT + 25-45d.

**Yield and Biomass:**

| Variable | Units   | Description                                           | Typical Range       |
|----------|---------|-------------------------------------------------------|---------------------|
| HWAH     | kg/ha   | Harvested yield (dry weight at harvest)               | 0-25000 (grain)     |
| HWAM     | kg/ha   | Harvested yield at maturity (dry weight)              | 0-25000 (grain)     |
| HWUM     | g       | Unit weight of harvested product (single grain/seed)  | 0.01-0.50           |
| CWAM     | kg/ha   | Tops (above-ground) biomass at maturity               | 500-30000           |
| BWAH     | kg/ha   | By-product (stover) harvested weight                  | 0-20000             |
| PWAM     | kg/ha   | Pod/ear weight at maturity                            | 0-20000             |
| LAIX     | m2/m2   | Maximum leaf area index during season                 | 0.5-8.0             |
| HIAM     | fraction| Harvest index (HWAM / CWAM)                           | 0.20-0.60 (grain)   |

**Water Balance:**

| Variable | Units   | Description                                           | Typical Range       |
|----------|---------|-------------------------------------------------------|---------------------|
| PRCM     | mm      | Cumulative precipitation during growing season        | 0-2000              |
| ETCM     | mm      | Cumulative evapotranspiration                         | 50-1000             |
| EPCM     | mm      | Cumulative plant transpiration                        | 30-700              |
| ESCM     | mm      | Cumulative soil evaporation                           | 20-400              |
| IRCM     | mm      | Cumulative irrigation applied                         | 0-1500              |
| ROCM     | mm      | Cumulative surface runoff                             | 0-500               |
| DRCM     | mm      | Cumulative vertical drainage                          | 0-800               |
| IRNUM    | count   | Number of irrigation applications                     | 0-100               |

**Nitrogen Balance:**

| Variable | Units      | Description                                        | Typical Range       |
|----------|------------|----------------------------------------------------|---------------------|
| NICM     | kg N/ha    | Cumulative inorganic N applied                     | 0-400               |
| NUCM     | kg N/ha    | Cumulative N uptake by crop                        | 20-300              |
| NFXM     | kg N/ha    | Cumulative N fixed (legumes only)                  | 0-300               |
| NLCM     | kg N/ha    | Cumulative N leached                               | 0-200               |
| CNAM     | kg N/ha    | Tops N content at maturity                         | 10-250              |
| GNAM     | kg N/ha    | Grain N content at maturity                        | 5-150               |

**Greenhouse Gas Emissions:**

| Variable | Units         | Description                                     | Typical Range       |
|----------|---------------|-------------------------------------------------|---------------------|
| N2OEM    | kg N/ha       | Cumulative N2O-N emissions                      | 0-10                |
| CO2EM    | kg C/ha       | Cumulative CO2-C from organic matter decomp     | 0-5000              |
| CH4EM    | kg C/ha       | Cumulative CH4-C emissions                      | 0-100 (paddy)       |
| TCEQM    | kg CO2eq/ha   | Total CO2-equivalent emissions                  | 0-10000             |

**Location Information:**

| Variable | Units   | Description                                           |
|----------|---------|-------------------------------------------------------|
| XCRD     | degrees | Longitude                                             |
| YCRD     | degrees | Latitude                                              |
| ELEV     | m       | Elevation above sea level                             |

#### Step 2.3: YYDDD Date Conversion

DSSAT uses YYDDD (2-digit year + 3-digit day of year) format throughout. The conversion rules are:

| YY Range | Century | Example YYDDD | Calendar Date    |
|----------|---------|---------------|------------------|
| 00-70    | 2000s   | 01100         | April 10, 2001   |
| 71-99    | 1900s   | 86076         | March 17, 1986   |

Conversion formula:
- If YY <= 70: Year = 2000 + YY
- If YY > 70: Year = 1900 + YY
- DDD = Day of Year (1-366)

To convert YYDDD to calendar date:
```python
yyddd = 86076
yy = yyddd // 1000
ddd = yyddd % 1000
year = 2000 + yy if yy <= 70 else 1900 + yy
# year=1986, day_of_year=76 -> March 17, 1986
```

**CRITICAL**: Do NOT confuse YYDDD with YYYYDDD. The value `2001100` would be interpreted as YY=200, DDD=1100, which is invalid. DSSAT always uses 2-digit years in output files.

#### Step 2.4: Handling Missing Values (-99)

The value -99 (integer) or -99.0 (real) means "not computed" or "not available." Source reference: All SUMDAT fields are initialized to -99 at SEASINIT (`OPSUM.for` lines 362-459).

**Decision tree for -99 values**:
- HWAH = -99: The simulation crashed before harvest. Check ERROR.OUT and PlantGro.OUT.
- ADAT = -99: Anthesis was never reached. The crop died or simulation ended before flowering.
- MDAT = -99: Maturity was never reached. The crop died or simulation ended before maturity.
- ETCM = -99: Water balance was not computed. Check ISWWAT switch (water simulation off?).
- NUCM = -99: Nitrogen was not simulated. Check ISWNIT switch.
- N2OEM = -99: GHG module was not active.

**NEVER treat -99 as a real data value.** If averaging Summary.OUT results across treatments, filter out -99 values first. Including -99 in an average will produce meaningless results.

---

### Step 3: Parse PlantGro.OUT for Daily Diagnostics

#### Step 3.1: PlantGro.OUT Structure

PlantGro.OUT contains daily plant growth variables for each treatment. The file has a header block for each treatment, followed by daily data lines.

Key diagnostic variables:

| Variable | Units    | Description                                              | Diagnostic Use                        |
|----------|----------|----------------------------------------------------------|---------------------------------------|
| XLAI     | m2/m2    | Leaf area index                                          | Canopy development tracking           |
| CWAD     | kg/ha    | Tops (above-ground) dry weight                           | Biomass accumulation                  |
| GWAD     | kg/ha    | Grain weight (dry)                                       | Yield formation                       |
| RWAD     | kg/ha    | Root weight (dry)                                        | Below-ground allocation               |
| SWFAC    | 0-1      | Soil water stress factor for photosynthesis              | 1=no stress, 0=max stress             |
| TURFAC   | 0-1      | Turgor water stress factor for expansion                 | 1=no stress, 0=max stress             |
| NSTRES   | 0-1      | Nitrogen stress factor                                   | 1=no stress, 0=max stress             |
| KSTRES   | 0-1      | Potassium stress factor                                  | 1=no stress, 0=max stress             |
| PSTRS1   | 0-1      | Phosphorus stress factor (photosynthesis)                | 1=no stress, 0=max stress             |
| PSTRS2   | 0-1      | Phosphorus stress factor (vegetative growth)             | 1=no stress, 0=max stress             |
| EWSD     | 0-1      | Excess water stress (waterlogging)                       | 1=no stress, 0=max stress             |

Source reference: Stress factor definitions from `Opgrow.for` lines 557-579:
- SWFAC: "Effect of soil-water stress on photosynthesis, 1.0=no stress, 0.0=max stress"
- TURFAC: "Water stress factor for expansion (0 - 1)"
- NSTRES: "Nitrogen stress factor (1=no stress, 0=max stress)"

#### Step 3.2: Reading Stress Patterns

To diagnose yield limitation, extract the daily stress factors and look for patterns:

1. **Water stress (SWFAC < 1.0)**: Indicates insufficient soil water. Check SoilWat.OUT for soil water depletion. Verify irrigation timing and amounts.
   - SWFAC drops to 0.5-0.7 for several days: moderate stress, yield reduction 10-30%.
   - SWFAC drops below 0.3 for extended periods: severe stress, major yield loss.

2. **Turgor stress (TURFAC < 1.0)**: Indicates water stress affecting leaf expansion. Typically occurs before SWFAC drops (expansion is more sensitive than photosynthesis).
   - TURFAC < 0.5 during vegetative phase: reduced LAI, smaller canopy.

3. **Nitrogen stress (NSTRES < 1.0)**: Indicates insufficient N for crop demand.
   - NSTRES < 0.8 during grain fill: significant yield and protein reduction.
   - Check NICM (N applied) vs NUCM (N uptake). If NUCM >> NICM, the crop is mining soil N.

4. **Combined stress identification**: Look for which stress factor drops first and stays lowest. The primary limiting factor is the one with the lowest average value during reproductive stages.

---

### Step 4: Parse SoilWat.OUT

SoilWat.OUT contains daily soil water content, drainage, and water balance terms by soil layer. Use this file to:

1. Verify initial soil water matches the IC specification (first day's values should match SH2O from FileX).
2. Track soil water depletion during stress periods identified in PlantGro.OUT.
3. Verify drainage and runoff are reasonable.
4. Check for waterlogging (water content near SAT for extended periods).

---

### Step 5: Interpret Evaluate.OUT

#### Step 5.1: Evaluate.OUT Structure

Evaluate.OUT is produced when measured data is available (from T-files or A-files) and IDETO='Y' or 'E'. It contains columns with `_S` suffix (simulated) and `_M` suffix (measured).

Source reference: `OPSUM.for` lines 112-117:
```fortran
Type EvaluateType
    INTEGER ICOUNT
    CHARACTER*6,  DIMENSION(EvaluateNum) :: OLAP
    CHARACTER*8,  DIMENSION(EvaluateNum) :: Simulated, Measured
    CHARACTER*50, DIMENSION(EvaluateNum) :: DESCRIP
End Type EvaluateType
```

#### Step 5.2: Reading Evaluate.OUT

Each row corresponds to one evaluation variable. The columns show:
- Variable label (e.g., HWAM, ADAT)
- Simulated value (_S suffix)
- Measured value (_M suffix)
- Difference and statistics

**How to interpret**:
- HWAM_S vs HWAM_M: Simulated vs measured yield. A close match (within 10-15%) indicates good calibration.
- ADAT_S vs ADAT_M: Simulated vs measured anthesis date. Should be within 3-5 days for a calibrated model.
- MDAT_S vs MDAT_M: Simulated vs measured maturity date. Should be within 5-7 days.

---

### Step 6: Sanity Checks for Output

#### Step 6.1: Yield Range Check

For grain crops, verify HWAH is within physically plausible bounds:

| Crop    | Code | Low Yield (kg/ha) | High Yield (kg/ha) | World Record (approx) |
|---------|------|--------------------|---------------------|-----------------------|
| Maize   | MZ   | 500                | 15000               | 33000                 |
| Wheat   | WH   | 300                | 10000               | 17000                 |
| Rice    | RI   | 400                | 12000               | 22000                 |
| Soybean | SB   | 200                | 5000                | 10000                 |
| Sorghum | SG   | 300                | 8000                | 15000                 |

If HWAH > 25000 for any grain crop, the simulation is likely erroneous. If HWAH = 0, the crop failed (see diagnostic procedure below).

#### Step 6.2: Phenological Order Check

Verify the following strict ordering:
```
PDAT < EDAT < ADAT < MDAT
```

- If EDAT = PDAT: Emergence was instantaneous (possible for transplants, impossible for seeds). Check PLME setting.
- If ADAT > MDAT: This violates biology and indicates a model error or wrong cultivar coefficients.
- If MDAT - PDAT is outside expected range for the crop, check cultivar thermal time parameters.

| Crop    | Typical EDAT-PDAT (days) | Typical ADAT-PDAT (days) | Typical MDAT-PDAT (days) |
|---------|--------------------------|--------------------------|--------------------------|
| Maize   | 5-12                     | 50-75                    | 90-140                   |
| Wheat   | 7-14                     | 70-130                   | 100-170                  |
| Rice    | 5-10                     | 55-90                    | 90-150                   |
| Soybean | 5-10                     | 35-60                    | 80-140                   |

#### Step 6.3: Water Balance Check

The water balance should approximately close:
```
PRCM + IRCM approximately equals ETCM + ROCM + DRCM + delta_SW
```

Where delta_SW is the change in soil water storage (initial minus final). An imbalance > 5% of total inputs indicates a problem.

Also verify:
- ETCM > 0 (some ET must occur if there is a crop growing).
- ETCM < PRCM + IRCM + initial_soil_water (ET cannot exceed total water supply).
- EPCM <= ETCM (transpiration is a component of ET).
- ESCM <= ETCM (soil evaporation is a component of ET).
- EPCM + ESCM should approximately equal ETCM.

#### Step 6.4: Nitrogen Balance Check

Verify:
- NUCM <= NICM + NFXM + initial_soil_N + mineralized_N (crop cannot take up more N than available).
- If NUCM >> NICM for a non-legume crop and no organic amendments, the soil N pools may be unrealistically high.

---

### Step 7: Diagnose Poor Simulation Results

#### Step 7.1: HWAH = 0 (Zero Yield)

**Diagnosis procedure**:
1. Open PlantGro.OUT. Does the crop emerge? (XLAI > 0 at any point?)
   - No emergence: Check planting depth (PLDP too deep?), soil water at planting (SH2O near LL?), soil temperature.
   - Emergence but no growth: Check stress factors on the day after emergence.
2. Check ADAT. Did the crop flower?
   - ADAT = -99: Crop died before flowering. Look for the day XLAI drops to 0 in PlantGro.OUT.
   - ADAT exists but MDAT = -99: Crop flowered but died before maturity. Severe late-season stress.
3. Check stress factors during flowering:
   - SWFAC < 0.2: Severe water stress killed the crop. Check irrigation and rainfall.
   - NSTRES < 0.2: Severe N stress. Check fertilizer applications.
4. Check management dates in MgmtEvent.OUT: Were irrigation and fertilizer actually applied?

#### Step 7.2: HWAH = -99 (Simulation Crashed)

**Diagnosis procedure**:
1. Open ERROR.OUT. Identify the ERRKEY and ERRNUM.
2. Cross-reference with MODEL.ERR for the full error description.
3. The line number (LNUM) in the error message indicates where in the input file the problem occurred.
4. Common causes: missing section in FileX, wrong format in input data, soil profile mismatch.

#### Step 7.3: Very Low Yield (HWAH < Expected by > 50%)

**Diagnosis procedure**:
1. Open PlantGro.OUT and extract daily SWFAC, NSTRES, TURFAC.
2. Calculate the average stress factor during grain fill (ADAT to MDAT):
   - Avg SWFAC < 0.7: Water stress is limiting. Increase irrigation or check weather data.
   - Avg NSTRES < 0.7: N stress is limiting. Increase fertilizer or check application timing.
3. Check LAIX (maximum LAI): If LAIX < 2.0 for maize or < 3.0 for wheat, the canopy was too small. This indicates early-season stress limiting leaf area expansion. Check TURFAC during vegetative phase.
4. Check cultivar coefficients: If phenology is wrong (too early/late maturity), the crop may not have enough time to fill grain.

#### Step 7.4: Wrong Phenology (Dates Off by > 10 Days)

**Diagnosis procedure**:
1. ADAT too early: Cultivar thermal time to flowering (P1 for maize, PHINT for wheat) is too small. Increase it.
2. ADAT too late: Thermal time to flowering is too large. Decrease it. Also check photoperiod sensitivity coefficients.
3. MDAT too early: Grain fill duration parameter (P5 for maize, P5/G3 for wheat) is too small.
4. MDAT too late: Grain fill duration is too large, or terminal stress is not being captured.
5. Check that weather data temperatures are reasonable for the location. Wrong temperature data directly affects thermal time accumulation.

---

### Step 8: Extract Results for Reporting

#### Step 8.1: Summary Statistics from Summary.OUT

For each treatment, extract and report:
```
Treatment | HWAH (kg/ha) | ADAT (date) | MDAT (date) | ETCM (mm) | NUCM (kg N/ha)
```

Convert YYDDD dates to calendar format for readability.

#### Step 8.2: Time Series from PlantGro.OUT

For graphical analysis, extract columns:
- Date (YYDDD), XLAI, CWAD, GWAD, SWFAC, NSTRES

Plot these as time series to visually assess crop growth trajectory and stress timing.

#### Step 8.3: Model Performance Statistics

When measured data is available, compute:

| Statistic | Formula                              | Good Value       | Description                    |
|-----------|--------------------------------------|------------------|--------------------------------|
| RMSE      | sqrt(mean((sim-obs)^2))             | < 15% of mean obs| Root mean square error         |
| d-index   | 1 - SS/sum((|Si-O_bar|+|Oi-O_bar|)^2) | > 0.90        | Willmott index of agreement    |
| R-squared | (correlation)^2                      | > 0.80           | Coefficient of determination   |
| MBE       | mean(sim - obs)                      | Near 0           | Mean bias error (+ = over)     |
| nRMSE     | RMSE / mean(obs) * 100              | < 15%            | Normalized RMSE                |

Tool reference: `parse_summary_out` extracts Summary.OUT data into a structured table. `parse_plantgro_out` extracts PlantGro.OUT into a time-series data frame.

## Expected Outputs

| Output                           | Format                      | Verification                                              |
|----------------------------------|-----------------------------|-----------------------------------------------------------|
| Parsed Summary.OUT table         | Tabular (CSV or dataframe)  | All treatments present; no unexpected -99 values          |
| Stress factor time series        | PlantGro.OUT extracts       | Stress periods identified and explained                   |
| Water balance verification       | Computed from Summary.OUT   | Balance closes within 5%                                  |
| Phenology comparison (if avail.) | Evaluate.OUT or manual      | Simulated dates within 5-7 days of observed               |
| Yield comparison (if available)  | Evaluate.OUT or manual      | Simulated within 15% of observed (nRMSE < 15%)           |
| Diagnostic report                | Text summary                | Root cause identified for any failed or poor simulations  |

## Validation Checks

1. **File existence**: All expected .OUT files exist and have content.
2. **Treatment count**: Number of data lines in Summary.OUT equals number of treatments in the batch file.
3. **No -99 in critical fields**: HWAH, ADAT, MDAT are not -99 for treatments expected to produce yield.
4. **Phenological order**: PDAT < EDAT < ADAT < MDAT for all treatments.
5. **Yield plausibility**: 0 < HWAH < 25000 for grain crops.
6. **Water balance closure**: |inputs - outputs - delta_storage| < 5% of total inputs.
7. **No error files**: ERROR.OUT does not exist or is empty.
8. **Warning review**: WARNING.OUT warnings are understood and benign.

## Common Pitfalls

| Pitfall                                           | Symptom                                              | Resolution                                                  |
|---------------------------------------------------|------------------------------------------------------|-------------------------------------------------------------|
| -99 in output mistaken for real values            | Nonsensical averages; negative yields in reports     | Always filter -99 before any arithmetic operations          |
| YYDDD format confused with YYYYDDD               | Dates off by decades; "year 8607" errors             | Remember: always 2-digit year (00-99) + 3-digit DOY         |
| Incomplete output from mid-simulation crash       | PlantGro.OUT has data but Summary.OUT is missing     | Crash occurred between OUTPUT and SEASEND phases            |
| Evaluating wrong treatment                        | Results don't match expectations                     | Cross-check treatment number in Summary.OUT header          |
| Ignoring WARNING.OUT                              | Subtle errors go undetected; wrong soil water init   | Always read WARNING.OUT after each simulation run           |
| Not checking MgmtEvent.OUT                        | Fertilizer or irrigation not applied as expected     | Verify all management events appear in MgmtEvent.OUT        |
| Comparing HWAM vs HWAH                            | Small discrepancy due to harvest losses              | HWAH includes harvest efficiency; HWAM is at-maturity yield |
| PlantGro.OUT stress factors not checked           | Yield discrepancy attributed to wrong cause          | Always examine SWFAC, NSTRES, TURFAC before adjusting cultivar |
| Reading output from a previous run                | Stale results from earlier simulation                | Check file timestamps; DSSAT overwrites, not appends        |
| Not distinguishing crop status codes (CRST)       | Mature crop confused with killed crop                | Check CRST in Summary.OUT: different codes for maturity vs death |
| Nitrogen.OUT absent when expected                 | ISWNIT='N' in simulation controls disables N output  | Set ISWNIT='Y' to enable nitrogen simulation and output     |
| GHG.OUT absent when expected                      | GHG module not activated or soil method incompatible | Verify MESSION and MESOL settings for GHG capability        |
