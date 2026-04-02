# S5: Simulation Controls Skill

## Purpose

Configure the *SIMULATION CONTROLS section of a DSSAT FileX to correctly specify simulation timing, process options, numerical methods, management automation, and output settings. This document defines every switch, its valid values, dependencies between switches, and the exact consequences of each setting so that no decision is left to inference.

## Prerequisites

- [ ] The FileX has been created with all data sections (*CULTIVARS, *FIELDS, *PLANTING DETAILS, etc.) already populated.
- [ ] The simulation period (start date, number of years) is known.
- [ ] The desired process complexity (water balance, nitrogen, phosphorus, etc.) has been decided.
- [ ] The evapotranspiration method has been selected based on available weather data.
- [ ] The organic matter model preference (CERES vs Century) has been determined.
- [ ] Output file requirements are known (which output files to generate, at what frequency).

## Inputs

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| SDATE | YYDDD | Simulation start date | `82056` |
| NYERS | Integer | Number of years to simulate | `1` |
| NREPS | Integer | Number of replications | `1` |
| Process switches | Characters | Y/N for each process | WATER=Y, NITRO=Y |
| Method selections | Characters | Single-char method codes | EVAPO=R, MESOM=G |
| Management modes | Characters | R=reported, A=automatic | PLANT=R, IRRIG=R |
| SMODEL | 8-char | Crop model override (optional) | `MZIXM048` or blank |

## Procedure

### Step 1: Understand the Section Structure

The *SIMULATION CONTROLS section consists of 5 mandatory sub-sections followed by an AUTOMATIC MANAGEMENT section. Each sub-section is on a single line, preceded by its own @-header line.

```
*SIMULATION CONTROLS
@N GENERAL     NYERS NREPS START SDATE RSEED SNAME.................... SMODEL
 1 GE              1     1     S 82056  2150 N X IRRIGATION, GAINESVI
@N OPTIONS     WATER NITRO SYMBI PHOSP POTAS DISES  CHEM  TILL   CO2
 1 OP              Y     Y     N     N     N     N     N     Y     M
@N METHODS     WTHER INCON LIGHT EVAPO INFIL PHOTO HYDRO NSWIT MESOM MESEV MESOL
 1 ME              M     M     E     R     S     R     R     1     G     R     2
@N MANAGEMENT  PLANT IRRIG FERTI RESID HARVS
 1 MA              R     R     R     N     M
@N OUTPUTS     FNAME OVVEW SUMRY FROPT GROUT CAOUT WAOUT NIOUT MIOUT DIOUT VBOSE CHOUT OPOUT FMOPT
 1 OU              N     Y     Y     1     Y     N     Y     Y     N     N     Y     N     Y     A
```

**Structure rule**: All sub-sections share the same @N number (simulation control level number). This number matches the SM factor code in the *TREATMENTS table. Multiple simulation control sets can exist (SM=1, SM=2, etc.) for different treatments.

### Step 2: Configure the GENERAL Line

```
@N GENERAL     NYERS NREPS START SDATE RSEED SNAME.................... SMODEL
 1 GE              1     1     S 82056  2150 N X IRRIGATION, GAINESVI
```

**Parameter definitions**:

| Parameter | Width | Type | Description | Valid Values | Default |
|-----------|-------|------|-------------|--------------|---------|
| N | 2 | Integer | Simulation control level number | 1-99 | 1 |
| GENERAL | 11 | Fixed text | Always "GE" (pad to column width) | GE | GE |
| NYERS | 6 | Integer | Number of years to simulate | 1-99 | 1 |
| NREPS | 6 | Integer | Number of replications | 1-999 | 1 |
| START | 6 | Character | Simulation start mode | S, A | S |
| SDATE | 6 | YYDDD | Simulation start date | Valid Julian date | Required |
| RSEED | 6 | Integer | Random seed for stochastic processes | 1-9999 | 2150 |
| SNAME | 25 | String | Simulation name (free text) | Any text | -- |
| SMODEL | 8 | String | Crop model override | Model code or blank | Blank (use DSSATPRO default) |

**START parameter**:
- `S` = Specified: Simulation begins on the date given in SDATE.
- `A` = Automatic: Simulation begins automatically based on planting window (used with automatic planting).

**Decision rule for SDATE**: Set SDATE to the day before or several days before the earliest management event (usually planting). SDATE MUST be on or before the planting date. If SDATE is after PDATE, the model will miss the planting event entirely and the crop will never be planted. A common practice is to set SDATE 1-30 days before planting to allow soil water balance to stabilize.

**SMODEL field**: If blank (spaces), DSSAT uses the default model from DSSATPRO.v48. If specified, the value must be a valid 8-character model code:

| SMODEL Value | Model |
|-------------|-------|
| MZCER048 | CERES-Maize |
| MZIXM048 | IXIM-Maize |
| CSCER048 | CropSim-CERES (Wheat default) |
| WHCRP048 | CropSim-Wheat |
| WHAPS048 | APSIM-Wheat (NWheat) |
| CRGRO048 | CROPGRO (soybean, peanut, dry bean, etc.) |
| RICER048 | CERES-Rice |
| SGCER048 | CERES-Sorghum |
| MLCER048 | CERES-Millet |
| PTSUB048 | SUBSTOR-Potato |
| SCCAN048 | CANEGRO-Sugarcane |
| CSYCA048 | CSYCA-Cassava |
| CSCAS048 | CSCAS-Cassava (legacy) |
| PIALO048 | ALOHA-Pineapple |
| TFAPS048 | APSIM-Teff |
| BSCER048 | CERES-Sugar beet |
| BACER048 | CERES-Barley |

**Failure mode**: If SMODEL specifies a model that does not match the crop code in the FileX, DSSAT will produce an error or use the wrong model entirely.

### Step 3: Configure the OPTIONS Line

```
@N OPTIONS     WATER NITRO SYMBI PHOSP POTAS DISES  CHEM  TILL   CO2
 1 OP              Y     Y     N     N     N     N     N     Y     M
```

**Switch definitions**:

| Switch | Width | Description | Valid Values | Default |
|--------|-------|-------------|--------------|---------|
| WATER | 6 | Water balance simulation | Y = Yes, N = No | Y |
| NITRO | 6 | Nitrogen simulation | Y = Yes, N = No | Y |
| SYMBI | 6 | Symbiotic N fixation (legumes) | Y = Yes, N = No | N (auto for legumes) |
| PHOSP | 6 | Phosphorus simulation | Y = Yes, N = No | N |
| POTAS | 6 | Potassium simulation | Y = Yes, N = No | N |
| DISES | 6 | Disease/pest simulation | Y = Yes, N = No | N |
| CHEM | 6 | Chemical application simulation | Y = Yes, N = No | N |
| TILL | 6 | Tillage simulation | Y = Yes, N = No | Y |
| CO2 | 6 | CO2 source | M = Measured from file, D = Default, W = Measured WTH | M |

**Critical switch dependencies** (enforced by the DSSAT code in IPSIM.for):

| Dependency Rule | Enforcement |
|----------------|-------------|
| If WATER = N, then NITRO is forced to N | Automatic (code: `IF (ISWWAT .EQ. 'N') THEN ISWNIT = 'N'`) |
| If WATER = N, then PHOSP is forced to N | Automatic |
| If NITRO = N, then PHOSP should be N | Recommended (model may not enforce) |
| SYMBI only applies to N-fixing crops | For non-legume crops, SYMBI is forced to N regardless of setting |

**Legume crops that support SYMBI = Y**: BN (dry bean), SB (soybean), PN (peanut), PE (pea), CH (chickpea), PP (pigeon pea), GY (guar), VB (velvet bean), CP (cowpea), CB (cabbage -- actually not a legume; DSSAT defines this list in code), FB (faba bean), GB (green bean), LT (lentil), AL (alfalfa), CV, BG (bambara groundnut). For all other crops, SYMBI is forced to N.

**CO2 switch values**:
- `M` = Measured: Uses CO2 values from the CO2 data file (CO2xxx.WDA). For historical simulations, this provides year-specific CO2 concentrations.
- `D` = Default: Uses a static CO2 concentration (380 ppm or the value defined in the CO2 data file for the simulation year). Used for sequence/seasonal runs.
- `W` = From weather file: Uses CO2 values if embedded in the weather data.

**Decision rule for CO2**: For experimental mode (replicating observed experiments), use `M` to get measured CO2 for the simulation year. For future scenario runs, use `D` or modify the CO2 file. For seasonal/forecast runs, DSSAT defaults to `D`.

**Decision rule for WATER = N**: Setting WATER = N runs the crop in "potential" mode -- no water stress. This is useful for estimating yield potential but disables all soil water processes. NITRO is automatically turned off as well (because N transport requires water flow). Only use WATER = N for diagnostic runs.

### Step 4: Configure the METHODS Line

```
@N METHODS     WTHER INCON LIGHT EVAPO INFIL PHOTO HYDRO NSWIT MESOM MESEV MESOL
 1 ME              M     M     E     R     S     R     R     1     G     R     2
```

**Extended format** (DSSAT v4.8 adds METMP and MEGHG columns):
```
@N METHODS     WTHER INCON LIGHT EVAPO INFIL PHOTO HYDRO NSWIT MESOM MESEV MESOL METMP MEGHG
 1 ME              M     M     E     R     S     R     R     1     G     R     2     D     0
```

**Method switch definitions**:

#### WTHER (Weather source method)
| Value | Description |
|-------|-------------|
| M | Measured: Read from .WTH file (standard mode) |
| G | Generated: Use internal weather generator from .CLI file |
| S | Simulated: Synthetic weather from distribution parameters |

**Decision rule**: Use `M` for all standard simulations where a .WTH file exists. Use `G` only for long-term risk assessment when no daily data is available.

#### INCON (Initial conditions method)
| Value | Description |
|-------|-------------|
| M | From file: Read from *INITIAL CONDITIONS section in FileX |
| S | As reported: Use soil profile defaults |

**Decision rule**: Use `M` when initial soil water and N content are known and specified in the FileX. Use `S` to let the model initialize from soil profile properties (typically lower limit for water, minimal N).

#### LIGHT (Light interception method)
| Value | Description |
|-------|-------------|
| E | Standard: Default light interception model |

**Decision rule**: Leave as `E`. This is not commonly changed.

#### EVAPO / MEEVP (Evapotranspiration method)
| Value | Description | Data Requirements |
|-------|-------------|-------------------|
| R | Ritchie: Modified Priestley-Taylor based on Ritchie (1972) | SRAD, TMAX, TMIN |
| P | Priestley-Taylor: Equilibrium evapotranspiration | SRAD, TMAX, TMIN |
| F | FAO-56 Penman-Monteith | SRAD, TMAX, TMIN, WIND, DEWP or RHUM |
| Z | ASCE Standardized Reference ET | SRAD, TMAX, TMIN, WIND, DEWP or RHUM |

**Decision rules for EVAPO**:
1. If you only have SRAD, TMAX, TMIN, RAIN -> use `R` (Ritchie) or `P` (Priestley-Taylor).
2. If you have WIND and DEWP/RHUM additionally -> you CAN use `F` (FAO-56) or `Z` (ASCE), which are more physically based.
3. If WIND data is missing and you select `F` or `Z`, DSSAT will use a default wind speed, which may produce inaccurate ET estimates.
4. For most applications, `R` (Ritchie) is the default and well-tested method.

#### INFIL / MEINF (Infiltration method)
| Value | Description |
|-------|-------------|
| S | SCS: SCS curve number method with mulch effects |
| N | SCS no mulch: SCS method without mulch effects |
| R | Ritchie: Ritchie steady-state infiltration |

**Decision rule**: Use `S` for most applications (includes mulch effects on runoff). Use `N` if mulch/residue cover should not affect infiltration.

#### PHOTO / MEPHO (Photosynthesis method)
| Value | Description |
|-------|-------------|
| L | Daily: Daily total photosynthesis calculation |
| C | Canopy hourly: Hourly canopy photosynthesis (more detailed) |

**Decision rule**: Use `L` for standard simulations. Use `C` for detailed canopy physiology studies. Note: not all crop models support `C` -- if the model does not support hourly photosynthesis, it will silently fall back to daily. DSSAT checks for model compatibility at runtime.

#### HYDRO (Hydrology method)
| Value | Description |
|-------|-------------|
| R | Ritchie: Ritchie cascading water balance |

**Decision rule**: Leave as `R`. This is the only widely tested option.

#### NSWIT (Nitrogen switch)
| Value | Description |
|-------|-------------|
| 1 | Standard nitrogen routines |

**Decision rule**: Leave as `1`. This is not commonly changed.

#### MESOM (Soil organic matter method)
| Value | Description |
|-------|-------------|
| G | Godwin/CERES: The original CERES organic matter decomposition module |
| P | Parton/Century: The Century-based soil organic matter module |

**Decision rules for MESOM**:
1. Use `G` (CERES/Godwin) for standard applications and where the soil has not been characterized for Century pools.
2. Use `P` (Century) for long-term sustainability assessments, soil carbon sequestration studies, or when detailed organic matter fractionation data is available.
3. The Century module requires additional soil organic matter pool initialization. If these are not available, the model uses default partitioning, which may not be accurate for the first 5-10 years.

#### MESEV (Soil evaporation method)
| Value | Description |
|-------|-------------|
| S | Suleiman-Ritchie: Updated soil evaporation (default in v4.8+) |
| R | Ritchie old: Original Ritchie two-stage evaporation |

**Decision rule**: Use `S` for new simulations (improved parameterization). Use `R` only for backward compatibility with older calibrations. Note: in the DSSAT source code default (IPSIM.for), the default when *SIMULATION CONTROLS is absent is `R` (old Ritchie), but the recommended setting is `S`.

#### MESOL (Soil layer redistribution)
| Value | Description |
|-------|-------------|
| 1 | Original: Use soil layers exactly as defined in .SOL file |
| 2 | New default: Model may redistribute layers for numerical stability |
| 3 | User-defined: Additional layer constraints |

**Decision rule**: Use `2` (new default) for most applications. Use `1` if you need exact layer boundaries (e.g., for sensor depth matching). Use `3` for advanced applications only.

#### METMP (Soil temperature method)
| Value | Description |
|-------|-------------|
| D | DSSAT improved: Kimball-based improved soil temperature (v4.8+ default) |
| E | EPIC: EPIC soil temperature routine |

**Decision rule**: Use `D` for new calibrations with v4.8. Note: the DSSAT v4.8 soil temperature changes required recalibration of some cultivar coefficients. If using old cultivar coefficients (pre-v4.8), results may differ from the original calibration.

#### MEGHG (Greenhouse gas emissions)
| Value | Description |
|-------|-------------|
| 0 | DSSAT original: Original DSSAT denitrification routine |
| 1 | DayCent N2O: DayCent-based N2O emission calculation |

**Decision rule**: Use `0` for standard crop simulation where GHG emissions are not of interest. Use `1` for environmental impact assessments that require N2O emission estimates.

### Step 5: Configure the MANAGEMENT Line

```
@N MANAGEMENT  PLANT IRRIG FERTI RESID HARVS
 1 MA              R     R     R     N     M
```

**Management switch definitions**:

| Switch | Width | Description | Valid Values |
|--------|-------|-------------|--------------|
| PLANT | 6 | Planting management | R = Reported (on specified date), A = Automatic (within planting window) |
| IRRIG | 6 | Irrigation management | R = Reported (on specified dates/amounts), A = Automatic, N = No irrigation, F = Fixed amount per event, D = Days after last irrigation |
| FERTI | 6 | Fertilizer management | R = Reported (on specified dates/amounts), A = Automatic, N = No fertilization, D = Days after planting |
| RESID | 6 | Residue management | R = Reported, N = Not applied, A = Automatic |
| HARVS | 6 | Harvest management | R = Reported date, M = At maturity, A = Automatic, G = At specified growth stage |

**PLANT switch details**:
- `R` = Reported: Plant on the date specified in *PLANTING DETAILS (PDATE). This is the standard mode for replaying observed experiments.
- `A` = Automatic: Plant within the window defined in @AUTOMATIC MANAGEMENT (PFRST to PLAST) when soil conditions (PH2OL, PH2OU, PH2OD) are met. Used for scenario analysis and optimization.

**IRRIG switch details**:
- `R` = Reported: Apply irrigation on the dates and amounts specified in *IRRIGATION section.
- `A` = Automatic: The model automatically irrigates when soil water drops below the threshold defined in @AUTOMATIC MANAGEMENT (ITHRL, ITHRU, IMDEP).
- `N` = No irrigation at all, regardless of *IRRIGATION section content.

**HARVS switch details**:
- `M` = Maturity: Harvest when the crop reaches physiological maturity (most common for grain crops).
- `R` = Reported: Harvest on the date specified in *HARVEST section.
- `A` = Automatic: Harvest within the window defined in @AUTOMATIC MANAGEMENT (HFRST to HLAST).
- `G` = Growth stage: Harvest at a specified growth stage.

### Step 6: Configure the OUTPUTS Line

```
@N OUTPUTS     FNAME OVVEW SUMRY FROPT GROUT CAOUT WAOUT NIOUT MIOUT DIOUT VBOSE CHOUT OPOUT FMOPT
 1 OU              N     Y     Y     1     Y     N     Y     Y     N     N     Y     N     Y     A
```

**Output switch definitions**:

| Switch | Width | Description | Valid Values |
|--------|-------|-------------|--------------|
| FNAME | 6 | Output file naming | N = Generic names, E = Experiment-specific names |
| OVVEW | 6 | Overview output file (OVERVIEW.OUT) | Y = Generate, N = Suppress |
| SUMRY | 6 | Summary output file (SUMMARY.OUT) | Y = Generate, N = Suppress |
| FROPT | 6 | Frequency of detailed output (days) | 1-365 (1 = daily, 7 = weekly) |
| GROUT | 6 | Growth output file (PlantGro.OUT) | Y = Generate, N = Suppress |
| CAOUT | 6 | Carbon output file (PlantC.OUT) | Y = Generate, N = Suppress |
| WAOUT | 6 | Water output file (SoilWat.OUT) | Y = Generate, N = Suppress |
| NIOUT | 6 | Nitrogen output file (SoilNi.OUT) | Y = Generate, N = Suppress |
| MIOUT | 6 | Phosphorus output file (SoilPi.OUT) | Y = Generate, N = Suppress |
| DIOUT | 6 | Disease output file | Y = Generate, N = Suppress |
| VBOSE | 6 | Verbose/detailed output | Y = Verbose, N = Minimal, 0 = None |
| CHOUT | 6 | Chemical output file | Y = Generate, N = Suppress |
| OPOUT | 6 | Operations output file (SoilTemp.OUT, etc.) | Y = Generate, N = Suppress |
| FMOPT | 6 | File format option | A = Standard ASCII |

**Decision rules for outputs**:
1. For standard evaluation: Set OVVEW=Y, SUMRY=Y, GROUT=Y, WAOUT=Y, NIOUT=Y. These provide the essential outputs for model evaluation.
2. For production runs (many treatments/years): Set non-essential outputs to N to reduce disk space and I/O time.
3. FROPT=1 provides daily output. FROPT=5 or FROPT=7 reduces output volume for long simulations.
4. VBOSE=Y provides detailed runtime information including growth stage transitions. Use for debugging.

### Step 7: Configure the AUTOMATIC MANAGEMENT Section

This section follows immediately after the OUTPUTS line and provides parameters for automatic planting, irrigation, nitrogen, residue, and harvest management.

```
@  AUTOMATIC MANAGEMENT
@N PLANTING    PFRST PLAST PH2OL PH2OU PH2OD PSTMX PSTMN
 1 PL          82050 82064    40   100    30    40    10
@N IRRIGATION  IMDEP ITHRL ITHRU IROFF IMETH IRAMT IREFF
 1 IR             30    50   100 GS000 IR001    10     1
@N NITROGEN    NMDEP NMTHR NAMNT NCODE NAOFF
 1 NI             30    50    25 FE001 GS000
@N RESIDUES    RIPCN RTIME RIDEP
 1 RE            100     1    20
@N HARVEST     HFRST HLAST HPCNP HPCNR
 1 HA              0 83057   100     0
```

#### Automatic Planting Parameters:

| Parameter | Description | Units |
|-----------|-------------|-------|
| PFRST | Earliest planting date | YYDDD |
| PLAST | Latest planting date | YYDDD |
| PH2OL | Lower soil water threshold for planting | % of available water |
| PH2OU | Upper soil water threshold for planting | % of available water |
| PH2OD | Soil depth for water check | cm |
| PSTMX | Maximum soil temperature for planting | degrees C |
| PSTMN | Minimum soil temperature for planting | degrees C |

**Decision rule**: Automatic planting is ONLY active when PLANT=A in the MANAGEMENT line. If PLANT=R, these parameters are read but ignored.

#### Automatic Irrigation Parameters:

| Parameter | Description | Units |
|-----------|-------------|-------|
| IMDEP | Management depth for irrigation decisions | cm |
| ITHRL | Lower threshold for irrigation trigger | % of available water |
| ITHRU | Upper threshold (target) after irrigation | % of available water |
| IROFF | Growth stage to turn off irrigation | Code (GS000=never off) |
| IMETH | Irrigation method code | IR001=overhead, etc. |
| IRAMT | Fixed irrigation amount per event | mm |
| IREFF | Irrigation efficiency | fraction (0-1) |

**Decision rule**: Automatic irrigation is ONLY active when IRRIG=A in the MANAGEMENT line. If IRRIG=R, the *IRRIGATION section data is used directly.

#### Automatic Harvest Parameters:

| Parameter | Description | Units |
|-----------|-------------|-------|
| HFRST | Earliest harvest date | YYDDD |
| HLAST | Latest harvest date | YYDDD |
| HPCNP | Harvest percentage (product) | % |
| HPCNR | Harvest percentage (byproduct/residue) | % |

### Step 8: Handle Switch Interactions and Dependencies

The following interaction rules are critical and are enforced in the DSSAT source code (IPSIM.for):

1. **WATER=N forces NITRO=N**: The code explicitly sets `ISWNIT = 'N'` when `ISWWAT = 'N'`. Nitrogen transport requires water flow. You cannot simulate nitrogen without water.

2. **WATER=N forces PHOSP=N**: Similarly, phosphorus simulation requires water.

3. **SYMBI only for N-fixing crops**: For any crop not in the legume list (BN, SB, PN, PE, CH, PP, GY, VB, CP, CB, FB, GB, LT, AL, BG), the code forces `ISWSYM = 'N'` regardless of the user setting.

4. **PHOSP=Y requires NITRO=Y**: While not strictly enforced in all code paths, phosphorus simulation depends on nitrogen cycling. Setting PHOSP=Y with NITRO=N will produce incomplete results.

5. **TILL=Y requires appropriate soil model**: Tillage modifies soil physical properties. If MESOL is not correctly set, tillage effects may not propagate properly.

6. **MEGHG=1 requires MESOM=P**: The DayCent N2O module is designed to work with the Century organic matter model. Using MEGHG=1 with MESOM=G (Godwin) may produce inconsistent results.

### Step 9: Handle Default Values

When the *SIMULATION CONTROLS section is ABSENT from the FileX (i.e., LNSIM=0), DSSAT uses these hardcoded defaults (from IPSIM.for):

| Parameter | Default Value |
|-----------|---------------|
| NYERS | 1 |
| NREPS | 1 |
| START | S |
| SDATE | Same as YRPLT (planting date) |
| RSEED | 2150 |
| WATER | Y |
| NITRO | Y |
| SYMBI | Y |
| PHOSP | N |
| POTAS | N |
| DISES | N |
| CHEM | N |
| TILL | Y |
| CO2 | D (for sequence/seasonal) or M (for experimental) |
| WTHER | M |
| INCON | M |
| LIGHT | E |
| EVAPO | R |
| INFIL | S |
| PHOTO | L |
| HYDRO | R |
| NSWIT | 1 |
| MESOM | G |
| MESOL | 2 |
| MESEV | R (old Ritchie) |
| METMP | D |
| MEGHG | 0 |
| PLANT | R |
| IRRIG | R |
| FERTI | R |
| RESID | R |
| HARVS | M |
| FROP | 3 |
| FNAME | N |
| OVVEW | Y |
| SUMRY | Y |
| GROUT | Y |
| CAOUT | N |
| WAOUT | N |
| NIOUT | N |
| MIOUT | N |
| DIOUT | N |
| VBOSE | N |
| CHOUT | N |
| OPOUT | Y |

**Decision rule**: If you want non-default behavior for any switch, you MUST include the *SIMULATION CONTROLS section. The defaults are reasonable for a basic water+nitrogen simulation but will NOT produce phosphorus, potassium, disease, or detailed soil carbon outputs.

### Step 10: Validate the Complete Simulation Controls

1. **SDATE vs PDATE**: Verify SDATE is on or before the planting date (PDATE from *PLANTING DETAILS). If SDATE is after PDATE, the simulation will never execute the planting event.

2. **SMODEL vs crop**: If SMODEL is specified, verify it is compatible with the crop code. A maize crop (CR=MZ) should have SMODEL starting with MZ (MZCER048 or MZIXM048). Setting SMODEL=RICER048 for a maize crop will crash.

3. **Switch consistency**: Verify the dependency rules from Step 8 are satisfied. Specifically:
   - If WATER=N, NITRO must also be N.
   - If PHOSP=Y, verify NITRO=Y and WATER=Y.

4. **Method compatibility with data**: If EVAPO=F or Z (Penman-Monteith), verify the .WTH file contains WIND and DEWP/RHUM columns.

5. **AUTOMATIC MANAGEMENT dates**: If PLANT=A, verify PFRST <= PLAST and both are valid Julian dates within the simulation period.

6. **SM factor level**: Verify the SM number in the *TREATMENTS table corresponds to an @N number in *SIMULATION CONTROLS.

7. **YYDDD format**: Verify all dates (SDATE, PFRST, PLAST, HFRST, HLAST) use the correct Y2K convention.

## Expected Outputs

| Output | Format | Verification |
|--------|--------|--------------|
| *SIMULATION CONTROLS section | 5 sub-lines + automatic management | All sub-lines present |
| Switch settings | Valid single-character codes | No blanks in required fields |
| Date consistency | SDATE <= PDATE | Checked against *PLANTING |
| Model compatibility | SMODEL matches crop | Verified against *CULTIVARS CR |

## Validation Checks

1. **REQUIRED**: All 5 sub-lines (GENERAL, OPTIONS, METHODS, MANAGEMENT, OUTPUTS) are present.
2. **REQUIRED**: SDATE is a valid YYDDD date.
3. **REQUIRED**: SDATE <= PDATE (simulation starts before or on planting date).
4. **REQUIRED**: All switch values are from the valid set for their respective parameter.
5. **REQUIRED**: If WATER=N, then NITRO=N (dependency enforced).
6. **REQUIRED**: SM factor level in *TREATMENTS matches @N in *SIMULATION CONTROLS.
7. **RECOMMENDED**: If EVAPO=F or Z, .WTH file includes WIND and DEWP columns.
8. **RECOMMENDED**: SMODEL matches the crop code from *CULTIVARS.
9. **RECOMMENDED**: FROPT >= 1 (output frequency is positive).
10. **RECOMMENDED**: RSEED is a positive integer (affects weather generation reproducibility).

## Common Pitfalls

1. **Inconsistent switch combinations**: Setting NITRO=Y with WATER=N. The code will silently force NITRO to N, but the user may not realize nitrogen is not being simulated. Always check: if WATER=N, all dependent processes (NITRO, PHOSP) are also N.

2. **SDATE after planting date**: If SDATE=82090 but PDATE=82057, the simulation starts 33 days after planting. The planting event is never executed because it falls before the simulation window. The crop is never planted, and the simulation produces empty output. Always verify: SDATE <= PDATE.

3. **Wrong SMODEL for crop**: Setting SMODEL=MZCER048 for a wheat experiment (CR=WH). The model will attempt to run maize physiology on a wheat crop and will either crash or produce nonsensical output. Always verify the first 2 characters of SMODEL match the crop code (MZ for maize, WH for wheat, SB for soybean, RI for rice, etc.). Exception: CROPGRO crops use CRGRO048 regardless of specific crop code.

4. **Missing AUTOMATIC MANAGEMENT when PLANT=A**: If PLANT is set to A (automatic) but the @AUTOMATIC MANAGEMENT section is missing or has invalid dates, DSSAT cannot determine when to plant. The crop may never be planted. Always include automatic management parameters when using A mode.

5. **MESEV mismatch with calibration**: The soil evaporation method (MESEV) affects soil water dynamics at the surface. If cultivar coefficients were calibrated using MESEV=R (old Ritchie) and you switch to MESEV=S (Suleiman-Ritchie), surface soil water will behave differently, potentially changing ET partitioning and crop water stress. Use the same MESEV that was used during calibration.

6. **MESOM=P without Century pool initialization**: Using the Century organic matter model (MESOM=P) without proper initialization of soil organic matter pools causes the model to use default partitioning, which may take 20-50 years of simulation to equilibrate. For short-term simulations (1-5 years), this can produce unrealistic N mineralization patterns. Use MESOM=G (Godwin) unless Century pools have been properly initialized.

7. **METMP change from pre-v4.8 calibrations**: DSSAT v4.8 introduced an improved soil temperature routine (METMP=D). Cultivar coefficients calibrated under the old routine (v4.7 and earlier) may need recalibration. If simulated phenology does not match historical observations after upgrading to v4.8, check whether METMP and cultivar coefficients are aligned.

8. **CO2=D in historical simulations**: Setting CO2=D uses a static default CO2 concentration. For historical simulations spanning decades (e.g., 1980-2020), CO2 has risen from ~340 to ~415 ppm. Using CO2=D with a fixed value will miss this trend. Use CO2=M with a CO2 data file that contains year-specific values.

9. **FROPT=0 producing no output**: If FROPT (output frequency) is set to 0, no detailed daily/periodic output files are generated. Set FROPT >= 1 for any detailed output.

10. **Multiple SM levels with different methods**: When different treatments use different simulation control sets (e.g., SM=1 with MESOM=G and SM=2 with MESOM=P), outputs may not be directly comparable because the treatments use different soil models. Document which methods apply to which treatments.
