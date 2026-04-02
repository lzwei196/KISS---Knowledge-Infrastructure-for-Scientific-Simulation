# S1: Experiment Design Skill

## Purpose

Define and construct a DSSAT FileX (experimental file) that serves as the central orchestration document linking weather, soil, genotype, management, and simulation control inputs into a single, machine-readable experiment specification. This document provides exact step-by-step instructions for creating, populating, and validating a FileX so that no decision point is left to inference.

## Prerequisites

- [ ] DSSAT v4.8.5 installation directory is known and accessible.
- [ ] The target crop has been identified (2-character crop code, e.g., MZ for maize).
- [ ] A weather station file (.WTH) exists and its 4-character station code (WSTA) is known.
- [ ] A soil profile exists in a .SOL file and its 10-character soil ID (ID_SOIL) is known.
- [ ] A cultivar entry exists in the appropriate .CUL file and its 6-character cultivar code (INGENO) is known.
- [ ] Experimental treatment structure (number of treatments, factor combinations) is defined on paper or in a design document.
- [ ] The user has read/write access to the DSSAT working directory.

## Inputs

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Crop code | 2-char string | DSSAT 2-letter crop identifier | `MZ` |
| Experiment name | Up to 10 chars | Descriptive experiment identifier | `UFGA8201MZ` |
| WSTA | 4-char string | Weather station code matching .WTH file | `UFGA` |
| ID_SOIL | 10-char string | Soil profile pedon code from .SOL file | `IBMZ910014` |
| INGENO | 6-char string | Cultivar code from .CUL file | `IB0035` |
| Treatment list | Structured table | Treatment names and factor level assignments | See procedure |
| Planting date | YYDDD | Julian date of planting | `82057` |
| Simulation start date | YYDDD | Julian date to begin simulation | `82056` |
| Management events | Structured lists | Irrigation, fertilizer, tillage schedules | See sections below |

## Procedure

### Step 1: Determine the File Extension

The FileX extension is composed of a period, the 2-character crop code, and the letter `X`. Select the extension based on the crop being simulated.

| Crop | Code | FileX Extension |
|------|------|-----------------|
| Maize | MZ | `.MZX` |
| Wheat | WH | `.WHX` |
| Soybean | SB | `.SBX` |
| Rice | RI | `.RIX` |
| Barley | BA | `.BAX` |
| Sorghum | SG | `.SGX` |
| Pearl millet | ML | `.MLX` |
| Peanut | PN | `.PNX` |
| Dry bean | BN | `.BNX` |
| Potato | PT | `.PTX` |
| Sugarcane | SC | `.SCX` |
| Cotton | CO | `.COX` |
| Sunflower | SU | `.SUX` |
| Tomato | TM | `.TMX` |
| Cassava | CS | `.CSX` |
| Chickpea | CH | `.CHX` |
| Pigeon pea | PP | `.PPX` |
| Cowpea | CP | `.CPX` |
| Sweet corn | SW | `.SWX` |
| Pineapple | PI | `.PIX` |
| Faba bean | FB | `.FBX` |
| Velvet bean | VB | `.VBX` |
| Taro | TR | `.TRX` |
| Tanier | TN | `.TNX` |
| Alfalfa | AL | `.ALX` |
| Bell pepper | PR | `.PRX` |
| Canola | CN | `.CNX` |
| Cabbage | CB | `.CBX` |
| Lentil | LT | `.LTX` |
| Quinoa | QU | `.QUX` |
| Safflower | SF | `.SFX` |
| Teff | TF | `.TFX` |
| Rye | RY | `.RYX` |
| Sugar beet | BS | `.BSX` |
| Guar | GY | `.GYX` |
| Hemp | HM | `.HMX` |
| Bambara groundnut | BG | `.BGX` |
| Chia | CI | `.CIX` |
| Strawberry | SR | `.SRX` |
| Sesame | SS | `.SSX` |
| Amaranth | AM | `.AMX` |
| Carinata | BC | `.BCX` |
| Bahia grass | BH | `.BHX` |
| Bermudagrass | BM | `.BMX` |
| Guinea grass | GG | `.GGX` |
| Green bean | GB | `.GBX` |

**Decision rule**: If no crop-specific extension applies or you are building a generic/multi-crop sequence experiment, use `.SNX` (sequence file). However, note that `.SNX` is used for sequence (rotation) experiments, NOT as a general-purpose fallback for single-crop experiments.

**Failure mode**: If you use the wrong extension (e.g., `.WHX` for a maize experiment), DSSAT will either fail to locate the correct crop model or will invoke the wrong model entirely. Always verify the extension matches the 2-character crop code.

### Step 2: Construct the 8-Character Filename

The filename follows the convention: `[SSSS][YY][TT]` where:

- `SSSS` = 4-character location/station code (typically matches WSTA, e.g., `UFGA`)
- `YY` = 2-digit year the experiment began (e.g., `82` for 1982)
- `TT` = 2-digit experiment number at that location and year (e.g., `01`)

**Full filename example**: `UFGA8201.MZX`

**Rules**:
1. The 4-character station code SHOULD match the WSTA code used in the *FIELDS section.
2. The year digits follow the Y2K convention: 0-70 maps to 2000-2070; 71-99 maps to 1971-1999.
3. The experiment number `TT` starts at `01` and increments for each additional experiment at the same location/year.
4. The full path is: `[DSSAT_DIR]/[CropFolder]/UFGA8201.MZX` or placed in a user-defined working directory.

### Step 3: Write the *EXP.DETAILS Header

This is the first non-blank, non-comment line in the file.

```
*EXP.DETAILS: UFGA8201MZ NIT X IRR, GAINESVILLE 2N*3I
```

**Format**: `*EXP.DETAILS:` followed by a space, then a free-form description (up to ~75 characters). Convention is to include the 8+2-char experiment ID (filename + crop code) and a brief description.

### Step 4: Write the *GENERAL Section

```
*GENERAL
@PEOPLE
 BENNETT,J.M. ZUR,B. HAMMOND,L.C. JONES,J.W.
@ADDRESS
 UNIVERSITY OF FLORIDA, GAINESVILLE, FL, USA
@SITE
 Irrigation Park, University of Florida
```

**Rules**:
- This section is OPTIONAL but strongly recommended for documentation.
- Each sub-header (@PEOPLE, @ADDRESS, @SITE) is followed by one data line.
- Lines are free-form text.
- If omitted, DSSAT will still run; this is metadata only.

### Step 5: Write the *TREATMENTS Section

This is the REQUIRED central routing table. It defines every treatment and maps each treatment to factor levels in every other section.

```
*TREATMENTS                        -------------FACTOR LEVELS------------
@N R O C TNAME.................... CU FL SA IC MP MI MF MR MC MT ME MH SM
 1 1 0 0 RAINFED LOW NITROGEN       1  1  0  1  1  1  1  0  0  0  0  0  1
 2 1 0 0 RAINFED HIGH NITROGEN      1  1  0  1  1  1  2  0  0  0  0  0  1
```

**Column definitions**:

| Column | Width | Description |
|--------|-------|-------------|
| N | 2 | Treatment number (1, 2, 3, ...) |
| R | 2 | Replication number (usually 1) |
| O | 2 | Rotation option (0 = not in rotation) |
| C | 2 | Sequence option (0 = not in sequence) |
| TNAME | 25 | Treatment name (free-form text, left-justified) |
| CU | 3 | Cultivar factor level -> *CULTIVARS @C number |
| FL | 3 | Field factor level -> *FIELDS @L number |
| SA | 3 | Soil analysis factor level -> *SOIL ANALYSIS (0 = not used) |
| IC | 3 | Initial conditions factor level -> *INITIAL CONDITIONS @C number |
| MP | 3 | Planting factor level -> *PLANTING DETAILS @P number |
| MI | 3 | Irrigation factor level -> *IRRIGATION @I number |
| MF | 3 | Fertilizer factor level -> *FERTILIZERS @F number |
| MR | 3 | Residue factor level -> *RESIDUES (0 = not used) |
| MC | 3 | Chemical factor level -> *CHEMICAL (0 = not used) |
| MT | 3 | Tillage factor level -> *TILLAGE (0 = not used) |
| ME | 3 | Environment factor level -> *ENVIRONMENT (0 = not used) |
| MH | 3 | Harvest factor level -> *HARVEST (0 = not used) |
| SM | 3 | Simulation controls factor level -> *SIMULATION CONTROLS @N number |

**Critical cross-referencing rule**: Every non-zero factor code in the treatment table MUST have a corresponding numbered entry in the referenced section. For example, if treatment 1 has `MI=2`, then the *IRRIGATION section must contain an entry with `@I` level 2.

**Decision rule for factor level 0**: A value of 0 means "this section does not apply to this treatment." For required sections (CU, FL, MP, SM), the value must be >= 1.

### Step 6: Write the *CULTIVARS Section

```
*CULTIVARS
@C CR INGENO CNAME
 1 MZ IB0035 McCurdy 84aa
```

**Format**:

| Field | Width | Description |
|-------|-------|-------------|
| C | 2 | Cultivar factor level (matches CU in treatments) |
| CR | 3 | 2-character crop code |
| INGENO | 7 | 6-character cultivar code (must exist in the .CUL file for the selected crop model) |
| CNAME | 20 | Cultivar name (free-form, for documentation) |

**Cross-reference**: INGENO must match a VAR# entry in the correct .CUL file. The .CUL file is selected based on the crop model (e.g., MZIXM048.CUL for IXIM maize, MZCER048.CUL for CERES-Maize). The model is determined by the SMODEL field in *SIMULATION CONTROLS or by the default in DSSATPRO.v48.

### Step 7: Write the *FIELDS Section

```
*FIELDS
@L ID_FIELD WSTA....  FLSA  FLOB  FLDT  FLDD  FLDS  FLST SLTX  SLDP  ID_SOIL    FLNAME
 1 UFGA0002 UFGA       -99     0 DR000     0     0 00000 -99    180  IBMZ910014 Field section
@L ...........XCRD ...........YCRD .....ELEV .............AREA .SLEN .FLWR .SLAS FLHST FHDUR
 1          29.638        -82.3689        40                 0     0     0     0   -99   -99
```

**Critical fields on the first line**:

| Field | Description | Validation |
|-------|-------------|------------|
| L | Field factor level (matches FL in treatments) | Must be >= 1 |
| ID_FIELD | 8-char field identifier | Free-form |
| WSTA | 4-char weather station code | **Must match the first 4 characters of a .WTH filename** |
| FLSA | Slope aspect (degrees) | -99 if unknown |
| FLOB | Obstruction to sun (%) | 0 if none |
| FLDT | Drainage type code | DR000=free drain, DR001=tile, etc. |
| SLDP | Soil depth (cm) | Must match or be <= max depth in .SOL |
| ID_SOIL | 10-char soil profile ID | **Must exactly match a profile header in the .SOL file** |

**Cross-references**:
- `WSTA` -> first 4 characters of the weather file name (e.g., `UFGA` -> `UFGA8201.WTH`)
- `ID_SOIL` -> pedon code in .SOL file (e.g., `IBMZ910014` -> `*IBMZ910014` line in SOIL.SOL)

**Second header line**: Contains latitude (XCRD), longitude (YCRD), elevation (ELEV), field area (AREA), slope length (SLEN), field width (FLWR), and SLA standard (SLAS). These are secondary metadata; -99 is acceptable for unknown values.

### Step 8: Write the *INITIAL CONDITIONS Section

```
*INITIAL CONDITIONS
@C   PCR ICDAT  ICRT  ICND  ICRN  ICRE  ICWD ICRES ICREN ICREP ICRIP ICRID ICNAME
 1    MZ 82056   100     0     1     1   -99  1000    .8     0   100    15 -99
@C  ICBL  SH2O  SNH4  SNO3
 1     5  .086    .5    .1
 1    15  .086    .5    .1
 1    30  .086    .5    .1
```

**Key fields**:

| Field | Description |
|-------|-------------|
| C | Initial conditions factor level (matches IC in treatments) |
| PCR | Previous crop code (2-char) |
| ICDAT | Date of initial conditions (YYDDD) |
| ICRT | Root weight from previous crop (kg/ha) |
| ICRES | Residue from previous crop (kg/ha) |
| ICBL | Soil layer bottom depth (cm) - must match or be subset of .SOL layer depths |
| SH2O | Initial soil water content (cm3/cm3) |
| SNH4 | Initial ammonium-N (ppm) |
| SNO3 | Initial nitrate-N (ppm) |

**Decision rule**: If initial conditions are unknown, set SH2O to the lower limit (SLLL from the .SOL file) for a "dry start" or to the drained upper limit (SDUL) for a "wet start." Set SNH4 and SNO3 to typical values (0.5-1.0 ppm) if unknown.

### Step 9: Write the *PLANTING DETAILS Section

```
*PLANTING DETAILS
@P PDATE EDATE  PPOP  PPOE  PLME  PLDS  PLRS  PLRD  PLDP  PLWT  PAGE  PENV  PLPH  SPRL                        PLNAME
 1 82057   -99   7.2   7.2     S     R    61     0     7   -99   -99   -99   -99     0                        -99
```

**Key fields**:

| Field | Description | Typical Values |
|-------|-------------|----------------|
| P | Planting factor level (matches MP in treatments) | 1, 2, ... |
| PDATE | Planting date (YYDDD) | Must be after SDATE in simulation controls |
| EDATE | Emergence date (YYDDD, -99 if simulated) | -99 |
| PPOP | Plant population at planting (plants/m2) | 5-10 for maize |
| PPOE | Plant population at emergence (plants/m2) | Same or less than PPOP |
| PLME | Planting method: S=seed, T=transplant, P=pregerminated, N=nursery | S |
| PLDS | Planting distribution: R=row, B=broadcast, H=hill | R |
| PLRS | Row spacing (cm) | 61-76 for maize |
| PLDP | Planting depth (cm) | 3-7 |

### Step 10: Write the *IRRIGATION AND WATER MANAGEMENT Section (if applicable)

```
*IRRIGATION AND WATER MANAGEMENT
@I  EFIR  IDEP  ITHR  IEPT  IOFF  IAME  IAMT IRNAME
 1     1   -99   -99   -99   -99   -99   -99 -99
@I IDATE  IROP IRVAL
 1 82063 IR001    13
```

**Structure**: Each irrigation level (matching MI in treatments) has:
1. A header line with efficiency (EFIR), depth (IDEP), threshold values
2. One or more event lines with date (IDATE, YYDDD), operation code (IROP), and amount (IRVAL, mm)

**Decision rule**: If MI=0 in the treatment table, this section can be omitted or left empty for that level. If MI=1, at least one event line or the header must be present.

### Step 11: Write the *FERTILIZERS (INORGANIC) Section (if applicable)

```
*FERTILIZERS (INORGANIC)
@F FDATE  FMCD  FACD  FDEP  FAMN  FAMP  FAMK  FAMC  FAMO  FOCD FERNAME
 1 82097 FE001 AP001    10    27     0     0     0     0   -99 -99
```

**Key fields**:

| Field | Description |
|-------|-------------|
| F | Fertilizer factor level (matches MF in treatments) |
| FDATE | Application date (YYDDD) |
| FMCD | Fertilizer material code (FE001=ammonium nitrate, FE005=urea, etc.) |
| FACD | Application method code (AP001=broadcast, AP002=banded, etc.) |
| FDEP | Depth of application (cm) |
| FAMN | N amount (kg N/ha) |
| FAMP | P amount (kg P2O5/ha) |
| FAMK | K amount (kg K2O/ha) |

### Step 12: Write Optional Sections (as needed)

The following sections are OPTIONAL and should only be included if the corresponding factor code in the treatment table is non-zero:

| Section | Marker | Factor Code | When to Include |
|---------|--------|-------------|-----------------|
| *TILLAGE | `@T TDATE TIMPL TDEP` | MT | Tillage operations planned |
| *RESIDUES | `@R RDATE RCOD RAMT RESN RESP RESK RINP RDEP RMET` | MR | Residue application planned |
| *CHEMICAL | `@C CDATE CHCOD CHAMT CHME CHDEP CHT CHNAME` | MC | Chemical applications planned |
| *HARVEST | `@H HDATE HSTG HCOM HSIZE HPC HBPC HNAME` | MH | Specific harvest management |
| *ENVIRONMENT | `@E OTEFG ETEFG ETEFG...` | ME | Controlled environment studies |
| *SOIL ANALYSIS | (rare) | SA | Measured soil analysis data |

**Decision rule**: If the factor code is 0 in the treatment table, do NOT include the section. If a section marker is present but empty, DSSAT may issue warnings.

### Step 13: Write the *SIMULATION CONTROLS Section

See S5 (Simulation Controls Skill) for the detailed specification. At minimum, the section must contain:

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

**Critical requirement**: SDATE must be on or before the earliest management event date (typically planting date). If SDATE is after planting date, the simulation will fail or produce incorrect results.

### Step 14: Write the @AUTOMATIC MANAGEMENT Section

This section follows immediately after *SIMULATION CONTROLS and provides parameters for automatic planting, irrigation, nitrogen, residue, and harvest management when the MANAGEMENT switches are set to 'A' (automatic).

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

### Step 15: Validate the Complete FileX

Run the following validation checks:

1. **Cross-reference WSTA**: Confirm that a file named `[WSTA]*.WTH` exists in the weather directory.
2. **Cross-reference ID_SOIL**: Confirm that the .SOL file contains a profile starting with `*[ID_SOIL]`.
3. **Cross-reference INGENO**: Confirm that the .CUL file for the selected model contains a line starting with the INGENO code.
4. **Factor level consistency**: For each treatment row, verify that every non-zero factor code has a matching numbered entry in its section.
5. **Date consistency**: Verify SDATE <= PDATE. Verify all management event dates (irrigation, fertilizer, tillage) fall within the simulation period.
6. **Section markers**: Verify that every section used by a treatment has its `*` marker line present.

**Tool reference**: `validate_filex_structure` -- invoke this tool with the FileX path to perform automated structural validation.

## Expected Outputs

| Output | Format | Verification |
|--------|--------|--------------|
| FileX file | `[SSSS][YY][TT].[CR]X` | File exists, is non-empty, and parseable |
| Section markers | All required `*` lines present | grep for `*TREATMENTS`, `*CULTIVARS`, `*FIELDS`, `*PLANTING`, `*SIMULATION` |
| Treatment table | Correct number of rows | Row count matches intended experiment design |
| Cross-references | All factor levels resolve | No orphan references, no missing section entries |

## Validation Checks

1. **REQUIRED**: The file begins with `*EXP.DETAILS:`.
2. **REQUIRED**: `*TREATMENTS` section exists and has at least one treatment row.
3. **REQUIRED**: `*CULTIVARS` section exists with at least one entry.
4. **REQUIRED**: `*FIELDS` section exists with at least one entry.
5. **REQUIRED**: `*PLANTING DETAILS` section exists with at least one entry.
6. **REQUIRED**: `*SIMULATION CONTROLS` section exists with all five sub-lines (GENERAL, OPTIONS, METHODS, MANAGEMENT, OUTPUTS).
7. **CONDITIONAL**: If any treatment has MF > 0, `*FERTILIZERS` section must exist with matching @F levels.
8. **CONDITIONAL**: If any treatment has MI > 0, `*IRRIGATION` section must exist with matching @I levels.
9. **CONDITIONAL**: If any treatment has IC > 0, `*INITIAL CONDITIONS` section must exist with matching @C levels.
10. **FORMAT**: All YYDDD dates use the correct Y2K convention (0-70 = 2000-2070, 71-99 = 1971-1999).
11. **FORMAT**: Fixed-width columns are properly aligned (DSSAT reads by column position, not by delimiter).

## Common Pitfalls

1. **Wrong crop extension**: Using `.MZX` for a wheat experiment or `.WHX` for maize. The model will not find the correct crop parameters. Always verify the extension matches the 2-character crop code.

2. **WSTA code mismatch**: The WSTA field in *FIELDS says `UFGA` but the weather file is named `GAIN8201.WTH`. DSSAT locates weather by matching WSTA to the first 4 characters of .WTH filenames. A mismatch produces "Weather file not found" errors.

3. **Factor level number mismatch**: Treatment table references MF=3 but *FERTILIZERS only has entries for @F 1 and @F 2. The simulation will crash with a "factor level not found" error.

4. **Factor level 0 vs missing section**: Setting MI=0 means "no irrigation for this treatment." This is valid even if the *IRRIGATION section exists with entries for other treatments. However, setting MI=1 when there is no *IRRIGATION section at all will cause a runtime error.

5. **SDATE after PDATE**: If simulation start date (SDATE in *SIMULATION CONTROLS) is later than planting date (PDATE in *PLANTING DETAILS), the model will miss critical early-season processes. Always set SDATE at least 1 day before PDATE (typically several days to a few weeks before).

6. **ID_SOIL not found in .SOL**: The 10-character ID_SOIL must exactly match (case-sensitive, including leading characters) a profile header in the active .SOL file. Common error: spaces in the ID or truncated characters.

7. **INGENO not in the correct .CUL file**: The cultivar code must exist in the .CUL file that matches the active crop model. If the user selects MZIXM (IXIM maize) but the cultivar only exists in MZCER048.CUL, the model will not find it. Verify which model is active via SMODEL in *SIMULATION CONTROLS or the default in DSSATPRO.v48.

8. **Fixed-width formatting errors**: DSSAT reads FileX data by fixed column positions. If data is shifted left or right by even one column, values will be read into the wrong variables. Use a text editor with column guides or a DSSAT-compatible editor to prevent this.

9. **Missing @-header lines**: Each section requires its `@` header line (e.g., `@N R O C TNAME...`). If the header is missing, the parser fails silently or reads garbage values.

10. **Comment lines**: Lines starting with `!` are comments and are ignored by the parser. Do not use `#` or `//` for comments -- only `!` is recognized.
