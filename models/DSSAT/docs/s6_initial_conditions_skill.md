# S6: Initial Conditions Specification

## Purpose

Define the starting state of the soil-plant system (water content, nitrogen pools, and previous crop residue) in the `*INITIAL CONDITIONS` section of the FileX experiment file, ensuring layer depths match the soil profile and values fall within physically valid ranges.

## Prerequisites

- [ ] S4 (Soil Profile) completed: a valid `.SOL` profile exists with defined layer depths (DS), lower limit (LL), drained upper limit (DUL), and saturation (SAT) for each layer.
- [ ] S5 (Weather) completed: simulation start date (SDATE) is known.
- [ ] The crop code for the previous crop (or `FA` for fallow) is known.
- [ ] You have access to the FileX being edited and the matching `.SOL` file.
- [ ] You know the target simulation purpose (single season vs. multi-year sequence) to decide spin-up requirements.

## Inputs

| Parameter | Type   | Source                | Description                                                  |
|-----------|--------|-----------------------|--------------------------------------------------------------|
| ICDAT     | YYDDD  | User / experiment log | Date of initial conditions measurement                       |
| PCR       | CHAR*2 | User / experiment log | Previous crop code (see crop code table below)               |
| ICRT      | REAL   | User / estimate       | Root weight remaining from previous crop (kg/ha)             |
| ICND      | REAL   | User / estimate       | Nodule weight from previous legume crop (kg/ha)              |
| ICRN      | REAL   | User / estimate       | Rhizobia number (0-1 scale, or count)                        |
| ICRE      | REAL   | User / estimate       | Rhizobium effectiveness (0-1 scale)                          |
| ICWD      | REAL   | User / estimate       | Initial water table depth (cm), -99 if not applicable        |
| ICRES     | REAL   | User / estimate       | Residue weight on surface (kg/ha)                            |
| ICREN     | REAL   | User / estimate       | Residue nitrogen concentration (%)                           |
| ICREP     | REAL   | User / estimate       | Residue phosphorus concentration (%)                         |
| ICRIP     | REAL   | User / estimate       | Incorporation percentage of surface residue (%)              |
| ICRID     | REAL   | User / estimate       | Incorporation depth of surface residue (cm)                  |
| SH2O(L)   | REAL   | Measurement / option  | Initial volumetric soil water content per layer (cm3/cm3)    |
| SNH4(L)   | REAL   | Measurement / estimate| Initial ammonium concentration per layer (ppm = ug N/g soil) |
| SNO3(L)   | REAL   | Measurement / estimate| Initial nitrate concentration per layer (ppm = ug N/g soil)  |

### Previous Crop Codes (PCR)

| Code | Crop         | Code | Crop        | Code | Crop       |
|------|--------------|------|-------------|------|------------|
| MZ   | Maize        | SB   | Soybean     | WH   | Wheat      |
| RI   | Rice         | SC   | Sugarcane   | BN   | Dry bean   |
| FA   | Fallow       | PN   | Peanut      | CO   | Cotton     |
| SG   | Sorghum      | BA   | Barley      | PT   | Potato     |

Use `FA` (fallow) when no previous crop was grown or when previous crop history is unknown.

## Procedure

### Step 1: Set the Initial Conditions Header Record

1.1. Locate the `*INITIAL CONDITIONS` section in the FileX. If it does not exist, create it after the `*FIELDS` section and before `*PLANTING DETAILS`.

1.2. Write the header line exactly as follows (spacing is column-fixed):
```
*INITIAL CONDITIONS
@C  PCR     ICDAT  ICRT  ICND  ICRN  ICRE  ICWD ICRES ICREN ICREP ICRIP ICRID
```

1.3. Write one data line below the header. The level number `@C` must match the IC level referenced in the `*TREATMENTS` section.

Example data line:
```
 1  MZ   86001   500     0  1.00  1.00   0.0  1000  0.80  0.00    15   100
```

Format reference from source code (`OPTEMPXY2K.for` line 420):
```
FORMAT (I3,1X,A2,4X,I7,2(1X,I5),2(1X,F5.2),1X,F5.1,1X,I5,2(1X,F5.2),2(1X,F5.0))
```

1.4. Validate each field:
- **PCR**: Must be a valid 2-character crop code from the table above. If unknown, use `FA`.
- **ICDAT**: Must be in YYDDD format. Must be <= SDATE (simulation start date). Typically set equal to SDATE.
- **ICRT**: Set to 0 after fallow. Set to 200-1000 kg/ha after a cereal crop. Set to 100-500 kg/ha after a legume.
- **ICND**: Set to 0 for non-legume previous crops. Set to 5-50 kg/ha after a legume.
- **ICRN**: Set to 1.00 if unknown. Range 0.00-1.00.
- **ICRE**: Set to 1.00 if unknown. Range 0.00-1.00.
- **ICWD**: Set to -99 if no water table. Otherwise, depth in cm from surface.
- **ICRES**: Residue weight in kg/ha. 0 if clean field. 500-5000 after cereal harvest. 200-1500 after legume.
- **ICREN**: Typical ranges: 0.5-1.0% for cereal residue, 1.5-3.0% for legume residue.
- **ICREP**: Typical range: 0.05-0.30%.
- **ICRIP**: 0-100%. 0 = residue left on surface. 100 = fully incorporated.
- **ICRID**: 0-30 cm. Depth to which residue is incorporated. Irrelevant if ICRIP = 0.

**Decision point**: If the previous crop is unknown and you want a "clean start," set PCR=FA, ICRT=0, ICND=0, ICRES=0, ICREN=0, ICREP=0, ICRIP=0, ICRID=0.

### Step 2: Set the Layer Data Records

2.1. Write the layer data header:
```
@C  ICBL  SH2O  SNH4  SNO3
```

2.2. Retrieve the layer depths from the soil profile (.SOL file). The soil layers are defined by the DS column (depth to bottom of layer in cm).

2.3. **CRITICAL**: The ICBL values in the initial conditions MUST exactly match the DS (layer bottom depth) values in the `.SOL` file. The model reads IC layer data positionally -- it reads NLAYR lines, one per soil layer (source: `SoilNi_init.for` lines 95-100). If the depths do not match, the model will assign water and nitrogen values to the wrong layers.

2.4. For each layer L (from 1 to NLAYR), write one line:
```
 1    15  .290   0.5  10.0
```

Format reference (`OPTEMPXY2K.for` line 430):
```
FORMAT(I3,1X,F5.0,1X,F5.3,2(1X,F5.1))
```

### Step 3: Set Initial Soil Water Content (SH2O)

Choose ONE of the following four approaches based on available information:

**Option 1: Use measured values per layer** (preferred when data available)
- Enter the measured volumetric water content for each layer.
- Verify: LL(L) <= SH2O(L) <= SAT(L) for every layer.
- If SH2O(L) < LL(L), the model will clamp it to LL (but this indicates a data problem).
- If SH2O(L) > SAT(L), the model will silently clamp to SAT. This is a common source of hidden error.

**Option 2: Set all layers to DUL** (field capacity start)
- Use when the field was recently irrigated or after a long wet period.
- For each layer: SH2O(L) = DUL(L) from the `.SOL` file.
- This is the most common default for irrigated trials.

**Option 3: Set all layers to LL** (wilting point start)
- Use for dry start conditions or severely drought-stressed initial state.
- For each layer: SH2O(L) = LL(L) from the `.SOL` file.
- Caution: This produces maximum initial water stress. Only use if you have evidence.

**Option 4: Fraction between LL and SAT**
- Calculate: SH2O(L) = LL(L) + fraction * (SAT(L) - LL(L))
- fraction = 0.0 gives LL (dry), fraction = 1.0 gives SAT (saturated).
- fraction = 0.5 approximates halfway between LL and SAT.
- fraction = (DUL(L) - LL(L)) / (SAT(L) - LL(L)) reproduces DUL.
- Use when you have a qualitative sense ("about 50% available water") but no measurements.

**Decision tree for choosing an option**:
1. Do you have measured soil moisture data? YES -> Option 1.
2. Is the field recently irrigated or at the end of wet season? YES -> Option 2 (DUL).
3. Is the field at the end of a long dry season with no irrigation? YES -> Option 3 (LL).
4. None of the above? -> Option 4 with fraction = 0.5, then calibrate.

### Step 4: Set Initial Nitrogen Content (SNO3, SNH4)

4.1. **Nitrate (SNO3)**: Units are ppm (ug NO3-N per g dry soil).
- Typical range: 1-20 ppm per layer.
- Nitrate generally decreases with depth: surface layers 5-20 ppm, deep layers 1-5 ppm.
- After long fallow: elevated NO3 near surface (10-25 ppm in top 30 cm) due to mineralization without crop uptake.
- After legume: elevated N throughout the profile (10-20 ppm through 60 cm).
- After heavily fertilized crop: moderate residual NO3 (5-15 ppm in top 60 cm).
- After unfertilized cereal: low NO3 (1-5 ppm throughout).
- After rice (paddy): very low NO3 (1-3 ppm) due to denitrification.

4.2. **Ammonium (SNH4)**: Units are ppm (ug NH4-N per g dry soil).
- Typical range: 0.5-5.0 ppm per layer.
- NH4 is typically more uniform with depth than NO3.
- In most upland soils: 0.5-3.0 ppm.
- In paddy soils after flooding: can be 5-15 ppm.
- NH4 is rapidly nitrified in aerobic soils, so initial values are less critical than NO3.

4.3. If the model is initialized with ISWNIT='N' (no nitrogen simulation), the source code sets NO3 and NH4 to 0.1 ppm as defaults (`SoilNi_init.for` line 104-105).

4.4. **Default recommendation when no measurements exist**:

| Depth (cm) | SNO3 (ppm) | SNH4 (ppm) | Scenario             |
|------------|------------|------------|----------------------|
| 0-15       | 10.0       | 3.0        | Moderate fertility   |
| 15-30      | 8.0        | 2.5        | Moderate fertility   |
| 30-60      | 5.0        | 2.0        | Moderate fertility   |
| 60-90      | 3.0        | 1.5        | Moderate fertility   |
| 90-150     | 2.0        | 1.0        | Moderate fertility   |
| 150+       | 1.0        | 0.5        | Moderate fertility   |

### Step 5: Apply Spin-Up Strategy (for Sequence or Multi-Year Runs)

5.1. **When to spin up**: If the simulation is part of a long-term sequence (RNMODE='Q') or you are uncertain about initial SOM pools, run a spin-up period.

5.2. **How to spin up**:
- Create a preliminary experiment that runs 2-5 years before the actual experiment period.
- Use the same weather data (repeat if necessary) and a simple management (fallow or continuous cropping).
- Set MESIC = 'M' in the simulation controls to let the model equilibrate the Soil Organic Matter (SOM) pools.
- After the spin-up, the model's internal SOM, microbial biomass, and inorganic N pools will be near equilibrium.

5.3. **Without spin-up**: If MESIC = 'M' is not set, the model uses the initial values directly. For single-season runs, this is acceptable if the initial conditions are well-characterized.

5.4. **MESIC = 'M' behavior**: The model runs a "mesic" initialization that takes 2 years of weather data to equilibrate SOM pools before the actual simulation begins. This is the recommended approach for long-term simulations.

### Step 6: Validate the Complete IC Section

6.1. Count the number of layer data lines. It MUST equal the number of layers in the soil profile (NLAYR in the `.SOL` file). The model reads exactly NLAYR lines (`SoilNi_init.for` lines 95-100); too few lines causes a read error, too many are ignored.

6.2. For each layer, verify:
- ICBL(L) == DS(L) from `.SOL` (exact match required).
- LL(L) <= SH2O(L) <= SAT(L).
- SNO3(L) >= 0.0.
- SNH4(L) >= 0.0.
- SNO3(L) <= 100 (values above this are physically implausible for most soils).
- SNH4(L) <= 50 (values above this are physically implausible for most upland soils).

6.3. Verify the header record:
- ICDAT <= SDATE (IC date must not be after simulation start).
- PCR is a valid 2-character crop code.
- All numeric fields are within the ranges listed in Step 1.4.

6.4. Tool reference: Run `validate_ic_vs_soil` to automate checks for layer depth matching and SH2O range validation.

## Expected Outputs

| Output                          | Format / Location                            | Verification                                        |
|---------------------------------|----------------------------------------------|-----------------------------------------------------|
| IC header line in FileX         | `*INITIAL CONDITIONS` section                | PCR, ICDAT, and all residue fields populated         |
| IC layer data in FileX          | Lines under `@C ICBL SH2O SNH4 SNO3` header | Number of lines == NLAYR; ICBL matches .SOL DS       |
| No model read errors            | No errors in MODEL.ERR referencing `*INITI`  | Section found and read without FORMAT errors         |
| Physically valid water content  | LL <= SH2O <= SAT for all layers             | No silent clamping to SAT                            |
| Plausible N values              | SNO3 and SNH4 within typical ranges          | No unrealistic early-season growth surge             |

## Validation Checks

1. **Layer depth match**: Extract DS values from `.SOL` and ICBL values from FileX. They must be identical arrays. If they differ, the model will read nitrogen and water values into mismatched layers, causing interpolation artifacts and wrong soil water dynamics.

2. **Water content bounds**: For every layer L, verify LL(L) <= SH2O(L) <= SAT(L). Values of SH2O > SAT are silently clamped to SAT by the model, hiding user error.

3. **Water content below DUL check**: If SH2O(L) < DUL(L) for all layers and the simulation is for an irrigated trial starting after rainfall, the initial conditions may be too dry. This produces spurious water stress at the start.

4. **Total profile water**: Sum SH2O(L) * DLAYR(L) across all layers. Compare to approximate field data if available. For a 150 cm profile: 15-50 cm of total water is typical.

5. **Nitrogen mass balance**: Convert SNO3 and SNH4 from ppm to kg/ha using the formula: kg/ha = ppm * BD(L) * DLAYR(L) / 10. Total profile inorganic N should be 20-200 kg N/ha for most agricultural soils.

6. **Post-simulation check**: After running, inspect the first few lines of `SoilWat.OUT` and `Nitrogen.OUT` to verify the initial values match what was specified.

## Common Pitfalls

| Pitfall                                       | Symptom                                                       | Resolution                                                     |
|-----------------------------------------------|---------------------------------------------------------------|----------------------------------------------------------------|
| IC layer depths do not match .SOL DS values    | Water/N assigned to wrong depths; anomalous drainage pattern   | Copy exact DS values from .SOL into ICBL column                |
| SH2O > SAT for one or more layers             | Silently clamped; no error message; unexpected drainage flux   | Check SAT in .SOL and ensure SH2O <= SAT                      |
| Very high initial NO3 (>30 ppm in all layers)  | Unrealistic early growth; crop grows too fast initially        | Reduce to measured or typical values; use spin-up               |
| Forgetting previous crop residue               | SOM pools underestimated; N mineralization too low             | Set ICRES, ICREN based on previous crop harvest                |
| ICDAT after SDATE                              | Model may read wrong IC values or use defaults                 | Set ICDAT <= SDATE; use SDATE if uncertain                     |
| Wrong number of IC layer lines                 | Fortran read error; simulation stops with error in MODEL.ERR   | Count lines; must equal NLAYR from .SOL file                   |
| Setting SH2O = 0 for "no water"               | SH2O below LL causes unexpected behavior                      | Use LL as the minimum value, never 0                           |
| PCR set to wrong crop                          | Incorrect initial residue decomposition; wrong C:N ratio       | Use actual previous crop code or FA if unknown                 |
| Missing IC section entirely                    | Model cannot find `*INITI` section; fatal error (code 42)      | Add the `*INITIAL CONDITIONS` section to FileX                 |
| Using YYYYDDD instead of YYDDD for ICDAT       | Date misread; simulation starts at wrong time                  | Use 2-digit year: 86001 not 1986001                            |
| NH4 and NO3 columns swapped                    | Model reads NH4 as NO3 and vice versa; wrong N dynamics        | Column order is always: ICBL SH2O SNH4 SNO3 (NH4 before NO3)  |
