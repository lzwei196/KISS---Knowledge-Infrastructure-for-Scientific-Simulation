# S4: Genotype Configuration Skill

## Purpose

Select, configure, and validate the genotype parameter files (.CUL, .ECO, .SPE) that define the physiological and morphological characteristics of the crop cultivar being simulated in DSSAT v4.8.5. This document specifies the file structure, coefficient definitions, cross-referencing rules, and validation checks for every step of genotype configuration.

## Prerequisites

- [ ] The crop model to be used has been identified (e.g., MZCER for CERES-Maize, MZIXM for IXIM-Maize, CRGRO for CROPGRO-Soybean).
- [ ] The cultivar to be simulated has been identified by name or variety code.
- [ ] The DSSAT Genotype directory is accessible (typically `[DSSAT_DIR]/Genotype/` or `[DSSAT_DIR]/Data/Genotype/`).
- [ ] The FileX has been created with a *CULTIVARS section referencing an INGENO code.
- [ ] The user understands the distinction between phenology coefficients (control development timing) and growth coefficients (control biomass and yield).

## Inputs

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Crop code | 2-char | DSSAT crop identifier | `MZ` |
| Model code | 5-char | Crop model identifier | `MZIXM` or `MZCER` |
| DSSAT version | 3-char | Version suffix for genotype files | `048` |
| INGENO | 6-char | Cultivar code (VAR#) | `IB0035` |
| Cultivar name | Up to 20-char | Descriptive name | `McCurdy 84aa` |
| ECO# | 6-char | Ecotype code linking .CUL to .ECO | `IB0001` |

## Procedure

### Step 1: Understand the Three-File Genotype Hierarchy

DSSAT uses three levels of genotype parameter files, from most specific to most general:

| File Type | Extension | Scope | Typical Changes |
|-----------|-----------|-------|-----------------|
| Cultivar | `.CUL` | Variety-specific coefficients | Calibrated per cultivar |
| Ecotype | `.ECO` | Group of cultivars sharing common traits | Rarely changed |
| Species | `.SPE` | Fundamental species-level parameters | Never changed by users |

**Data flow**: The model reads all three files. Cultivar coefficients in .CUL override or supplement ecotype parameters from .ECO, which in turn reference species-level constants from .SPE.

**Rule**: Users typically only modify .CUL files. Do not modify .SPE files unless you are a model developer. Modify .ECO files only when creating a new ecotype group.

### Step 2: Determine the Correct File Names

File names follow the convention: `[CROP][MODEL]048.[EXT]`

| Component | Description | Example |
|-----------|-------------|---------|
| CROP | 2-char crop code | `MZ` |
| MODEL | 3-char model abbreviation | `IXM` (IXIM), `CER` (CERES), `GRO` (CROPGRO) |
| 048 | DSSAT version 4.8 suffix | `048` |
| EXT | File type extension | `CUL`, `ECO`, `SPE` |

**Complete file name examples**:

| Crop | Model | .CUL File | .ECO File | .SPE File |
|------|-------|-----------|-----------|-----------|
| Maize (CERES) | MZCER | MZCER048.CUL | MZCER048.ECO | MZCER048.SPE |
| Maize (IXIM) | MZIXM | MZIXM048.CUL | MZIXM048.ECO | MZIXM048.SPE |
| Wheat (CERES) | WHCER | WHCER048.CUL | WHCER048.ECO | WHCER048.SPE |
| Wheat (CROPSIM) | WHCRP | WHCRP048.CUL | WHCRP048.ECO | WHCRP048.SPE |
| Wheat (APSIM) | WHAPS | WHAPS048.CUL | WHAPS048.ECO | WHAPS048.SPE |
| Soybean | SBGRO (=CRGRO) | SBGRO048.CUL | SBGRO048.ECO | SBGRO048.SPE |
| Rice | RICER | RICER048.CUL | RICER048.ECO | RICER048.SPE |
| Sorghum | SGCER | SGCER048.CUL | SGCER048.ECO | SGCER048.SPE |
| Pearl millet | MLCER | MLCER048.CUL | MLCER048.ECO | MLCER048.SPE |
| Peanut | PNGRO | PNGRO048.CUL | PNGRO048.ECO | PNGRO048.SPE |
| Dry bean | BNGRO | BNGRO048.CUL | BNGRO048.ECO | BNGRO048.SPE |
| Potato | PTSUB | PTSUB048.CUL | PTSUB048.ECO | PTSUB048.SPE |
| Sugarcane (CANEGRO) | SCCAN | SCCAN048.CUL | SCCAN048.ECO | SCCAN048.SPE |
| Cotton | COGRO | COGRO048.CUL | COGRO048.ECO | COGRO048.SPE |
| Sunflower | SUGRO (=CRGRO) | SUGRO048.CUL | SUGRO048.ECO | SUGRO048.SPE |
| Tomato | TMGRO | TMGRO048.CUL | TMGRO048.ECO | TMGRO048.SPE |
| Cassava (CSYCA) | CSYCA | CSYCA048.CUL | CSYCA048.ECO | CSYCA048.SPE |
| Barley (CERES) | BACER | BACER048.CUL | BACER048.ECO | BACER048.SPE |
| Chickpea | CHGRO | CHGRO048.CUL | CHGRO048.ECO | CHGRO048.SPE |
| Cowpea | CPGRO | CPGRO048.CUL | CPGRO048.ECO | CPGRO048.SPE |
| Pigeon pea | PPGRO | PPGRO048.CUL | PPGRO048.ECO | PPGRO048.SPE |
| Faba bean | FBGRO | FBGRO048.CUL | FBGRO048.ECO | FBGRO048.SPE |
| Teff | TFAPS | TFAPS048.CUL | TFAPS048.ECO | TFAPS048.SPE |
| Alfalfa | ALFRM | ALFRM048.CUL | ALFRM048.ECO | ALFRM048.SPE |
| Pineapple | PIALO | PIALO048.CUL | -- | PIALO048.SPE |
| Taro | TRARO | TRARO048.CUL | -- | TRARO048.SPE |
| Tanier | TNARO | TNARO048.CUL | -- | TNARO048.SPE |
| Sweet corn | SWCER | SWCER048.CUL | SWCER048.ECO | SWCER048.SPE |

**Model selection via DSSATPRO**: The default model for each crop is defined in `DSSATPRO.v48`. The `M` prefix lines map crop codes to model executables:
```
MMZ C: \DSSAT48 DSCSM048.EXE MZCER048   (default maize model is CERES)
MWH C: \DSSAT48 DSCSM048.EXE CSCER048   (default wheat model is CROPSIM-CERES)
MSB C: \DSSAT48 DSCSM048.EXE CRGRO048   (default soybean model is CROPGRO)
MRI C: \DSSAT48 DSCSM048.EXE RICER048   (default rice model)
```

**Override via SMODEL**: The SMODEL field in *SIMULATION CONTROLS of the FileX can override the default model. If SMODEL is blank, the default from DSSATPRO is used.

### Step 3: Understand the .CUL File Format

The .CUL file header (title line) identifies the model:
```
*MAIZE CULTIVAR COEFFICIENTS: MZIXM048 MODEL
```

**Comment lines**: Lines starting with `!` are comments. Comments include coefficient definitions, calibration notes, and historical changes.

**Column header line**: Starts with `@` and defines the coefficient column positions:
```
@VAR#  VRNAME.......... EXPNO   ECO#    P1    P2    P5    G2    G3 PHINT    AX   ALL
```

**Common fixed columns** (present in all .CUL files):

| Column | Name | Width | Description |
|--------|------|-------|-------------|
| 1 | VAR# | 6 | Cultivar identification code (this is INGENO in the FileX) |
| 2 | VRNAME | 16-20 | Cultivar name |
| 3 | EXPNO | 6 | Number of experiments used for calibration (informational; `.` if unknown) |
| 4 | ECO# | 6 | Ecotype code linking to .ECO file |
| 5+ | Coefficients | Variable | Model-specific cultivar coefficients |

### Step 4: Key Coefficient Definitions by Crop Model

#### CERES-Maize (MZCER048.CUL)

| Coefficient | Description | Units | Control | Range |
|-------------|-------------|-------|---------|-------|
| P1 | Thermal time from emergence to end of juvenile phase (base 8 C) | degree-days | Phenology | 5.0-450.0 |
| P2 | Delay per hour photoperiod increase above 12.5 h | days/hour | Phenology | 0.000-2.000 |
| P5 | Thermal time from silking to physiological maturity (base 8 C) | degree-days | Phenology | 580.0-999.0 |
| G2 | Maximum possible number of kernels per plant | number | Growth/Yield | 248.0-990.0 |
| G3 | Kernel filling rate under optimum conditions | mg/day | Growth/Yield | 5.00-16.50 |
| PHINT | Phylochron interval (thermal time between leaf tip appearances) | degree-days | Phenology | 38.00-75.00 |

**Calibration priority for CERES-Maize**:
1. P1, P2, P5, PHINT -- calibrate to match observed anthesis and maturity dates
2. G2, G3 -- calibrate to match observed kernel number and grain yield

#### IXIM-Maize (MZIXM048.CUL)

| Coefficient | Description | Units | Control | Range |
|-------------|-------------|-------|---------|-------|
| P1 | Thermal time from emergence to end of juvenile phase (base 8 C) | degree-days | Phenology | 5.0-450.0 |
| P2 | Delay per hour photoperiod increase above 12.5 h | days/hour | Phenology | 0.100-0.800 |
| P5 | Thermal time from silking to physiological maturity (base 8 C) | degree-days | Phenology | 500.0-1100.0 |
| G2 | Maximum possible number of kernels on topmost ear | number | Growth/Yield | 400.0-1100.0 |
| G3 | Kernel filling rate under optimum conditions | mg/day | Growth/Yield | 4.0-20.0 |
| PHINT | Phylochron interval | degree-days | Phenology | 38.00-55.00 |
| AX | Leaf surface area of largest leaf | cm2/leaf | Growth | 200.0-850.0 |
| ALL | Leaf longevity of most longevous leaf | degree-days | Growth | 600.0-900.0 |

**Note**: IXIM has 2 additional coefficients (AX, ALL) compared to CERES-Maize. These control canopy light interception and leaf area dynamics.

#### CERES-Wheat (WHCER048.CUL)

| Coefficient | Description | Units | Control | Range |
|-------------|-------------|-------|---------|-------|
| P1V | Vernalization days required (optimum temperature) | days | Phenology | 0-60 |
| P1D | Photoperiod response (% reduction in rate per 10 h drop in photoperiod) | %/10h | Phenology | 0-200 |
| P5 | Grain filling phase duration (excluding lag) | degree-days C | Phenology | 100-999 |
| G1 | Kernel number per unit canopy weight at anthesis | #/g | Growth/Yield | 10-50 |
| G2 | Standard kernel size under optimum conditions | mg | Growth/Yield | 10-80 |
| G3 | Standard non-stressed mature tiller weight (including grain) | g dwt | Growth/Yield | 0.5-8.0 |
| PHINT | Interval between successive leaf tip appearances | degree-days C | Phenology | 30-150 |

**Calibration priority for CERES-Wheat**:
1. P1V, P1D -- calibrate to match anthesis timing (P1V critical for winter wheats)
2. P5 -- calibrate to match maturity date
3. G1, G2, G3 -- calibrate to match yield components

#### CROPGRO-Soybean (SBGRO048.CUL = CRGRO048)

| Coefficient | Description | Units | Control | Range |
|-------------|-------------|-------|---------|-------|
| CSDL | Critical short day length below which no daylength effect | hours | Phenology | 11.78-14.60 |
| PPSEN | Slope of response to photoperiod (positive for short-day) | 1/hour | Phenology | 0.129-0.385 |
| EM-FL | Time from emergence to first flower (R1) | photothermal days | Phenology | 9.0-28.9 |
| FL-SH | Time from first flower to first pod (R3) | photothermal days | Phenology | 5.0-10.0 |
| FL-SD | Time from first flower to first seed (R5) | photothermal days | Phenology | 11.0-22.0 |
| SD-PM | Time from first seed (R5) to physiological maturity (R7) | photothermal days | Phenology | 22.00-37.70 |
| FL-LF | Time from first flower to end of leaf expansion | photothermal days | Phenology | 15.00-26.00 |
| LFMAX | Maximum leaf photosynthesis rate (30 C, 350 ppm CO2, high light) | mg CO2/m2-s | Growth | 1.000-1.400 |
| SLAVR | Specific leaf area under standard conditions | cm2/g | Growth | 300-400 |
| SIZLF | Maximum size of full leaf (three leaflets) | cm2 | Growth | 137.0-230.0 |
| XFRT | Maximum fraction of daily growth to seed + shell | fraction | Growth | 1.00 |
| WTPSD | Maximum weight per seed | g | Growth/Yield | 0.15-0.19 |
| SFDUR | Seed filling duration for pod cohort | photothermal days | Growth/Yield | 17.0-25.5 |
| SDPDV | Average seed per pod | #/pod | Growth/Yield | 1.70-2.44 |
| PODUR | Time to reach final pod load | photothermal days | Growth | 8.0-12.0 |
| THRSH | Threshing percentage (seed/(seed+shell)) | % | Growth | 76.0-78.0 |
| SDPRO | Fraction protein in seeds | g/g | Quality | 0.400-0.405 |
| SDLIP | Fraction oil in seeds | g/g | Quality | 0.200-0.205 |

**Calibration priority for CROPGRO-Soybean**:
1. CSDL, PPSEN, EM-FL, SD-PM -- control maturity group and phenology timing
2. LFMAX, SLAVR -- control canopy photosynthesis and light interception
3. WTPSD, SFDUR, SDPDV -- control yield components

#### CERES-Rice (RICER048.CUL)

| Coefficient | Description | Units | Control | Range |
|-------------|-------------|-------|---------|-------|
| P1 | GDD from emergence during basic vegetative phase (base 9 C) | degree-days | Phenology | 150.0-800.0 |
| P2R | Delay in GDD per hour increase above P2O | degree-days/hour | Phenology | 5.0-300.0 |
| P5 | GDD from grain filling start to maturity (base 9 C) | degree-days | Phenology | 150.0-850.0 |
| P2O | Critical photoperiod (longest day for max development rate) | hours | Phenology | 11.0-13.0 |
| G1 | Potential spikelet number per g main culm dry weight | #/g | Growth/Yield | 50.0-70.0 |
| G2 | Single grain weight under ideal conditions | g | Growth/Yield | 0.015-0.030 |
| G3 | Tillering coefficient relative to IR64 | scalar | Growth | 0.70-1.30 |
| PHINT | Phyllochron interval | degree-days C | Phenology | 55.0-90.0 |
| THOT | Temperature above which spikelet sterility is affected | degrees C | Growth | 25.0-34.0 |
| TCLDP | Temperature below which panicle initiation is delayed | degrees C | Phenology | 12.0-18.0 |
| TCLDF | Temperature below which spikelet sterility is affected by cold | degrees C | Growth | 10.0-20.0 |

**Note on rice model evolution**: In DSSAT v4.8, the old G4 and G5 coefficients were removed and replaced by THOT, TCLDP, and TCLDF. If converting from older versions, use: `THOT = 28.0/G4`, `TCLDP = 15.0*G5`, `TCLDF = 15.0*G5`.

### Step 5: Cross-Reference INGENO from FileX to .CUL

The FileX *CULTIVARS section contains:
```
@C CR INGENO CNAME
 1 MZ IB0035 McCurdy 84aa
```

The INGENO code (`IB0035`) must match a VAR# entry in the .CUL file:
```
IB0035 McCurdy 84aa         . IB0001 260.0 0.300 955.0 700.0  8.50 43.00  770.  930.
```

**Matching rules**:
1. INGENO is matched character-for-character (6 characters) to VAR# in .CUL.
2. The match is case-sensitive.
3. If INGENO is not found in the .CUL file, DSSAT will issue an error and stop.
4. The crop code (CR) in the FileX must match the crop for the .CUL file.

**Decision rule on which .CUL file is searched**: DSSAT searches the .CUL file that corresponds to the active crop model. The active model is determined by:
1. SMODEL in *SIMULATION CONTROLS (if specified), OR
2. The default model from DSSATPRO.v48 `M[CR]` line

If SMODEL specifies MZIXM but the cultivar IB0035 only exists in MZCER048.CUL and not in MZIXM048.CUL, the model will fail to find the cultivar.

### Step 6: Cross-Reference ECO# from .CUL to .ECO

Each cultivar entry in .CUL contains an ECO# field:
```
IB0035 McCurdy 84aa         . IB0001 260.0 ...
                               ^^^^^^
                               ECO# = IB0001
```

This ECO# must match an entry in the corresponding .ECO file. For example, in MZIXM048.ECO:
```
@ECO#  ECONAME.........  TBASE TOPT  ROPT   P20  DJTI  GDDE  DSGFT  RUE   KCAN  PSTM  PEAR  TSEN  CDAY
IB0001 HEAVY STEMS         8.0 34.0  34.0  12.5   4.0   6.0   170.  4.2   0.85  0.75  0.15
```

**Ecotype parameters** (example for MZIXM):

| Parameter | Description | Units |
|-----------|-------------|-------|
| TBASE | Base temperature for development | degrees C |
| TOPT | Optimum temperature for vegetative development | degrees C |
| ROPT | Optimum temperature for reproductive development | degrees C |
| P20 | Daylength below which no daylength effect | hours |
| DJTI | Minimum days from juvenile to tassel initiation | days |
| GDDE | GDD per cm seed depth for emergence | GDD/cm |
| DSGFT | GDD from silking to effective grain fill | degree-days C |
| RUE | Radiation use efficiency | g/MJ PAR |
| KCAN | Canopy light extinction coefficient | dimensionless |

**Decision rule**: If the ECO# in the .CUL file does not match any entry in the .ECO file, the model may use default values or crash, depending on the crop model. Always verify the ECO# linkage.

### Step 7: Understand MINIMA/MAXIMA Validation Rows

Most .CUL files contain special entries with VAR# codes `999991` (MINIMA) and `999992` (MAXIMA):

```
999991 MINIMA               . DFAULT   5.0 0.100 500.0 400.0   4.0 38.00 200.0 600.0
999992 MAXIMA               . DFAULT 450.0 0.800 1100. 1100.  20.0 55.00 850.0 900.0
```

**Purpose**: These rows define the valid range for each coefficient. They are NOT used as cultivar data during simulation. They serve as documentation of acceptable coefficient ranges.

**Validation rule**: For each cultivar coefficient, verify that the value falls between the MINIMA and MAXIMA values. If a coefficient is outside this range, it may produce unrealistic phenology or yield with NO runtime error. This is a silent failure mode.

**Example check for MZIXM IB0035**:
```
P1 = 260.0  (MINIMA=5.0, MAXIMA=450.0)   -> OK
P2 = 0.300  (MINIMA=0.100, MAXIMA=0.800)  -> OK
P5 = 955.0  (MINIMA=500.0, MAXIMA=1100.)  -> OK
G2 = 700.0  (MINIMA=400.0, MAXIMA=1100.)  -> OK
G3 = 8.50   (MINIMA=4.0, MAXIMA=20.0)     -> OK
PHINT=43.00 (MINIMA=38.00, MAXIMA=55.00)  -> OK
```

### Step 8: Add a New Cultivar Entry

To add a new cultivar to an existing .CUL file:

1. Open the .CUL file in a text editor.
2. Locate the end of the existing cultivar entries (before any closing comments).
3. Add a new line following the exact column format of the @-header.
4. Assign a unique 6-character VAR# code that does not conflict with existing entries.
5. Set the ECO# to an existing ecotype from the .ECO file.
6. Enter coefficient values. Start with values from a similar known cultivar and adjust.

**New entry template** (for MZIXM):
```
XX0001 MY NEW CULTIVAR      . IB0001 200.0 0.500 800.0 750.0  8.00 43.00  700.  800.
```

**VAR# naming conventions**:
- `IB` prefix = IBSNAT/DSSAT standard cultivars
- `PC` prefix = calibration placeholder cultivars
- `99` prefix = generic maturity group representatives
- User-created cultivars: use institution-specific 2-letter prefix (e.g., `UF` for Univ. of Florida)

### Step 9: Calibration Overview

Calibration is the process of adjusting .CUL coefficients to match observed experimental data.

**Two-phase calibration approach**:

**Phase 1: Phenology** (adjust timing coefficients first)
1. Compare simulated anthesis/flowering date with observed.
2. If simulated flowering is too early, INCREASE phenology coefficients (P1, P5 for maize; P1V, P1D, P5 for wheat; EM-FL, SD-PM for soybean).
3. If simulated flowering is too late, DECREASE phenology coefficients.
4. Repeat until simulated and observed anthesis/maturity dates match within 3-5 days.

**Phase 2: Growth/Yield** (adjust growth coefficients second)
1. After phenology is correct, compare simulated yield with observed.
2. If simulated yield is too low, INCREASE growth coefficients (G2, G3 for maize; G1, G2 for wheat; LFMAX, WTPSD for soybean).
3. If simulated yield is too high, DECREASE growth coefficients.
4. Also consider: SLPF in soil, SRGF distribution, initial conditions.

**Critical rule**: Always calibrate phenology BEFORE yield. If phenology is wrong, yield adjustments will compensate for the wrong growth duration and will not generalize to other environments.

### Step 10: Validate the Genotype Configuration

1. **INGENO exists in .CUL**: Search the .CUL file for the exact 6-character VAR# code.
2. **ECO# exists in .ECO**: Search the .ECO file for the exact ECO# code from the .CUL entry.
3. **Coefficients within MINIMA/MAXIMA**: Every coefficient value falls between the MINIMA and MAXIMA rows.
4. **Correct model match**: The .CUL file name matches the model specified in DSSATPRO or SMODEL.
5. **Crop code consistency**: The CR field in the FileX *CULTIVARS section matches the crop for the genotype files.
6. **No duplicate VAR#**: The 6-character VAR# is unique within the .CUL file (if not, the first match is used).

## Expected Outputs

| Output | Format | Verification |
|--------|--------|--------------|
| .CUL file entry | Fixed-width row with VAR#, VRNAME, ECO#, coefficients | INGENO found in file |
| .ECO file entry | Fixed-width row with ECO#, ecotype parameters | ECO# from .CUL resolves |
| Cross-reference chain | FileX INGENO -> .CUL VAR# -> .ECO ECO# | All links valid |
| Coefficient values | Within MINIMA-MAXIMA range | No out-of-range values |

## Validation Checks

1. **REQUIRED**: INGENO from FileX matches a VAR# in the correct .CUL file.
2. **REQUIRED**: ECO# from the .CUL entry matches an ECO# in the corresponding .ECO file.
3. **REQUIRED**: The .CUL file name matches the active crop model (MZIXM048.CUL for IXIM, MZCER048.CUL for CERES, etc.).
4. **REQUIRED**: All coefficient values are numeric (no blanks in required positions).
5. **RECOMMENDED**: All coefficients fall within MINIMA-MAXIMA bounds.
6. **RECOMMENDED**: Phenology coefficients have been validated against observed flowering/maturity data.
7. **REQUIRED**: The .SPE file for the model exists in the Genotype directory.
8. **REQUIRED**: For CROPGRO models, the species file defines the crop-specific photo/thermal response -- ensure SBGRO048.SPE (not a generic file) is used for soybean.

## Common Pitfalls

1. **Wrong model selected (MZCER vs MZIXM)**: CERES-Maize (MZCER) and IXIM-Maize (MZIXM) are different models with different coefficient sets. MZCER uses 6 coefficients (P1, P2, P5, G2, G3, PHINT). MZIXM uses 8 (adds AX, ALL). Using MZCER coefficients in MZIXM will work (AX and ALL will get defaults), but using MZIXM's broader coefficient ranges in MZCER will produce different results because MZCER has different internal algorithms. Always verify which model is active before selecting the .CUL file.

2. **Coefficient outside MINIMA/MAXIMA gives wrong phenology with no error**: DSSAT does NOT enforce the MINIMA/MAXIMA bounds at runtime. If you set P1=800 in CERES-Maize (MAXIMA=450), the model will run without error but the simulated crop will have an unrealistically long juvenile phase, never reaching maturity in the growing season. This is a silent failure -- the model runs, produces output, but the output is meaningless. Always manually verify against MINIMA/MAXIMA.

3. **ECO# mismatch**: If the ECO# in the .CUL file (e.g., `IB0002`) does not exist in the .ECO file, the model may crash or silently use default ecotype parameters. Always verify the ECO# linkage. Common error: copying a cultivar line from one .CUL file to another without checking that the ECO# exists in the target model's .ECO file.

4. **Wrong .CUL file for the crop model**: If SMODEL is blank in the FileX and the DSSATPRO default for maize is MZCER, but you added your cultivar only to MZIXM048.CUL, DSSAT will search MZCER048.CUL and not find your cultivar. Solution: either add the cultivar to the correct .CUL file or set SMODEL explicitly in *SIMULATION CONTROLS.

5. **Overwriting existing cultivar entries**: When editing a .CUL file, do not modify the standard IBSNAT cultivars (IB0001-IB0070, etc.) as these are used by the standard test experiments. Add new cultivars at the end of the file with unique VAR# codes.

6. **Decimal alignment errors**: .CUL files use fixed-width columns. If a coefficient value is wider than its column (e.g., `1050.0` in a 6-character field), it overflows into the next column. Always format numbers to fit within the designated column width.

7. **Confusing G2 definitions across crops**: In CERES-Maize, G2 = maximum kernels per plant (hundreds to ~1000). In CERES-Rice, G2 = single grain weight in grams (0.015-0.030). In CERES-Wheat, G2 = standard kernel size in mg (10-80). These are completely different parameters that happen to share the same name. Never transfer G2 values between crop models.

8. **Using old (pre-v4.8) cultivar coefficients**: DSSAT v4.8 introduced changes to soil temperature calculations that require recalibrated cultivar coefficients. Old coefficients (from v4.7 or earlier) may produce different phenology results. Check for comments in .CUL files that note version-specific recalibration, e.g.: `! 4.8.0 cultivar coefficients (before changes in soil temperature subroutine)`.

9. **Missing .SPE file**: If the species parameter file is missing or corrupted, the model cannot run at all. This file is installed with DSSAT and should never need user modification. If it is missing, reinstall or copy from a clean DSSAT installation.

10. **Blank SMODEL with non-default model needed**: If you want to use MZIXM but SMODEL is left blank in the FileX, DSSAT will use the default model from DSSATPRO (which for maize is MZCER). You must explicitly set SMODEL to the desired model code or ensure the DSSATPRO default matches your intent.
