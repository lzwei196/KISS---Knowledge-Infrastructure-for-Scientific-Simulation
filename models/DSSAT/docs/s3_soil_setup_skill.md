# S3: Soil Setup Skill

## Purpose

Create, configure, and validate a DSSAT soil profile within a .SOL file so that it accurately represents the physical, chemical, and hydraulic properties of the soil at the experimental site. This document specifies the exact format, parameter definitions, layer construction rules, and quality checks needed for a valid soil input.

## Prerequisites

- [ ] Soil texture, depth, and basic properties of the target site are known (from field measurements, soil survey, or pedotransfer estimation).
- [ ] A 10-character pedon code has been assigned or chosen.
- [ ] The .SOL file to which the profile will be added has been located (typically `SOIL.SOL` in the soil directory).
- [ ] The user understands the distinction between lower limit (SLLL), drained upper limit (SDUL), and saturation (SSAT).
- [ ] Layer depth boundaries have been decided based on horizon data or standard layering scheme.

## Inputs

| Parameter | Type | Units | Description | Example |
|-----------|------|-------|-------------|---------|
| Pedon code | 10-char string | -- | Unique soil profile identifier | `IBMZ910014` |
| Source institution | 10-char string | -- | Data source | `IBSNAT` |
| Soil texture class | 3-char string | -- | USDA texture abbreviation | `SIC` |
| Profile depth | Integer | cm | Total soil depth | `210` |
| Description | Free text | -- | Profile description | `DEFAULT - DEEP SILTY CLAY` |
| SALB | Float | 0-1 | Soil albedo | `0.11` |
| SLU1 | Float | mm | Stage 1 evaporation upper limit | `6.0` |
| SLDR | Float | 0-1 | Drainage rate fraction | `0.30` |
| SLRO | Float | -- | SCS runoff curve number | `85.0` |
| SLNF | Float | 0-1 | N mineralization factor | `1.00` |
| SLPF | Float | 0-1 | Photosynthesis/growth factor | `1.00` |
| Layer data | Table | Various | Per-layer soil properties | See procedure |

## Procedure

### Step 1: Understand the .SOL File Structure

A single .SOL file can contain MULTIPLE soil profiles. Each profile is delimited by a line starting with `*` followed by the 10-character pedon code. Profiles are read sequentially; the model searches for the profile matching ID_SOIL from the FileX.

**File-level structure**:
```
*SOILS: General DSSAT Soil Input File
! DSSAT v4.8; comments
!
! ... comment block ...
!
*IB00000001  IBSNAT      SIC     210 DEFAULT - DEEP SILTY CLAY
@SITE        COUNTRY          LAT     LONG SCS FAMILY
 ...
@ SCOM  SALB  SLU1  SLDR  SLRO  SLNF  SLPF  SMHB  SMPX  SMKE
 ...
@  SLB  SLMH  SLLL  SDUL  SSAT  SRGF  SSKS  SBDM  SLOC  SLCL  SLSI  SLCF  SLNI  SLHW  SLHB  SCEC  SADC
 ...layer data rows...

*IB00000002  IBSNAT      SIC     150 DEFAULT - MEDIUM SILTY CLAY
...next profile...
```

**Rule**: Each profile starts with `*` on column 1. The parser reads everything between one `*` line and the next `*` line (or end of file) as a single profile.

### Step 2: Construct the Pedon Code

The 10-character pedon code (ID_SOIL) is the primary key that links the FileX to the soil profile.

**Convention**: `[SS][CC][NN][NNNN]`
- `SS` = 2-character source code (e.g., `IB` = IBSNAT, `US` = US, etc.)
- `CC` = 2-character country or crop code
- `NN` = 2 digits for soil category
- `NNNN` = 4-digit sequence number

**Examples**:
- `IB00000001` = IBSNAT generic profile #1
- `IBMZ910014` = IBSNAT, maize-related, profile from 1991, #14
- `UFGA000001` = University of Florida, Gainesville, #1

**Rules**:
1. Must be exactly 10 characters (padded with spaces if needed, but convention uses numbers/letters to fill).
2. Must be unique within the .SOL file.
3. Must match EXACTLY (character-for-character) what appears in the FileX ID_SOIL field.

### Step 3: Write the Profile Header Line

```
*IBMZ910014  IBSNAT      SIC     210 DEFAULT - DEEP SILTY CLAY
```

**Format** (fixed-width):

| Position | Content | Description |
|----------|---------|-------------|
| 1 | `*` | Profile delimiter marker |
| 2-11 | Pedon code (10 chars) | Unique identifier |
| 13-24 | Source (12 chars) | Institution/source |
| 25-30 | Texture class (5 chars) | USDA soil texture abbreviation |
| 31-37 | Depth (6 chars) | Profile depth in cm |
| 38+ | Description (free text) | Profile description |

**Valid USDA texture classes**: S, LS, SL, SCL, SC, SIC, SICL, SIL, SI, CL, L, C

### Step 4: Write the Site Information Lines

```
@SITE        COUNTRY          LAT     LONG SCS FAMILY
 Generic     Generic          -99      -99 Generic
```

**Fields**:
- SITE: Site name (up to 12 chars)
- COUNTRY: Country name (up to 12 chars)
- LAT: Latitude (decimal degrees, -99 if unknown)
- LONG: Longitude (decimal degrees, -99 if unknown)
- SCS FAMILY: Soil classification family (free text)

**Decision rule**: If site coordinates are unknown, use -99. This line is metadata and does not affect simulation. However, populating it aids future users.

### Step 5: Write the Surface Parameters Line

```
@ SCOM  SALB  SLU1  SLDR  SLRO  SLNF  SLPF  SMHB  SMPX  SMKE
   -99  0.11   6.0  0.30  85.0  1.00  1.00 IB001 IB001 IB001
```

**Parameter definitions**:

| Parameter | Width | Units | Description | Range | Default |
|-----------|-------|-------|-------------|-------|---------|
| SCOM | 5 | -- | Soil color (code, -99 if unknown) | -99, BL, BR, etc. | -99 |
| SALB | 6 | 0-1 | Soil surface albedo (bare, dry) | 0.05-0.25 | Texture-dependent |
| SLU1 | 6 | mm | Stage 1 evaporation upper limit | 2.0-12.0 | 6.0 |
| SLDR | 6 | 0-1 | Drainage rate (fraction/day) | 0.05-0.80 | 0.30 |
| SLRO | 6 | -- | SCS curve number | 40-99 | Texture/slope-dependent |
| SLNF | 6 | 0-1 | Nitrogen mineralization factor | 0.5-1.5 | 1.00 |
| SLPF | 6 | 0-1 | Photosynthesis/growth factor | 0.5-1.0 | 1.00 |
| SMHB | 6 | code | pH in buffer method code | IB001, etc. | IB001 |
| SMPX | 6 | code | Extractable phosphorus method code | IB001, etc. | IB001 |
| SMKE | 6 | code | Exchangeable potassium method code | IB001, etc. | IB001 |

**Guidance for SALB**:
| Soil Color/Texture | SALB |
|---------------------|------|
| Dark clay soils | 0.09-0.11 |
| Medium-textured soils | 0.12-0.14 |
| Sandy soils | 0.15-0.20 |
| Light/calcareous soils | 0.20-0.25 |

**Guidance for SLDR**:
| Drainage Class | SLDR |
|----------------|------|
| Very poorly drained | 0.05-0.10 |
| Poorly drained | 0.10-0.20 |
| Moderately drained | 0.20-0.40 |
| Well drained | 0.40-0.60 |
| Excessively drained | 0.60-0.80 |

**Guidance for SLRO** (SCS Curve Number):
| Soil Hydrologic Group | SLRO Range |
|----------------------|------------|
| Group A (sand, loamy sand) | 40-60 |
| Group B (silt loam, loam) | 55-75 |
| Group C (sandy clay loam) | 70-85 |
| Group D (clay, silty clay) | 80-95 |

**Decision rule for SLPF**: Set SLPF = 1.00 unless you have evidence of a site-specific yield limitation not captured by other soil parameters (e.g., toxic levels of aluminum, unnamed nutrient deficiency). SLPF < 1.0 reduces potential photosynthesis and biomass. SLPF is sometimes used as a calibration factor during model evaluation; initial setup should use 1.00.

### Step 6: Design the Layer Structure

DSSAT soil profiles consist of discrete layers, each defined by its bottom depth (SLB in cm). Layer structure must follow these rules:

**Hard limits**:
1. **Maximum 20 layers** (NL=20 in the DSSAT code). More than 20 layers will be silently truncated -- layers beyond the 20th will be ignored without warning.
2. **Layer depths must be strictly monotonically increasing**: Each SLB must be greater than the previous.
3. **First layer top is always 0 cm** (the soil surface).

**Recommended layer structure**:

| Layer | Bottom Depth (SLB) | Thickness | Rationale |
|-------|-------------------|-----------|-----------|
| 1 | 5 cm | 5 cm | Thin surface layer for seed zone and evaporation |
| 2 | 15 cm | 10 cm | Root zone near surface |
| 3 | 30 cm | 15 cm | Mid-root zone |
| 4 | 45 cm | 15 cm | Transition zone |
| 5 | 60 cm | 15 cm | Main root zone |
| 6 | 90 cm | 30 cm | Deep root zone |
| 7 | 120 cm | 30 cm | Subsoil |
| 8 | 150 cm | 30 cm | Deep subsoil |
| 9 | 180 cm | 30 cm | Deep subsoil |
| 10 | 210 cm | 30 cm | Profile bottom |

**Decision rules for layer design**:
1. **Top layer must be <= 5 cm**: A top layer thicker than 5 cm causes numerical instability in the surface energy balance and evaporation calculations. If your soil survey reports a 0-20 cm horizon, split it into 0-5 and 5-15 (or 5-20) cm layers.
2. **Thinner layers near surface, thicker at depth**: The surface layers control evaporation, germination, and early root growth. Use 5 cm for layer 1, 10 cm for layers 2-3, then progressively thicker layers (15, 30, 45 cm).
3. **Match layer boundaries to soil horizons if possible**: If your soil survey reports an A horizon at 0-25 cm and a B horizon at 25-60 cm, set layer boundaries at 25 and 60 cm.
4. **Shallow soils**: If the total soil depth is < 20 cm, DSSAT may encounter division-by-zero errors in some calculations. The minimum recommended total soil depth is 20 cm. If the actual soil is shallower, set the last layer to at least 20 cm and use very low root growth factor (SRGF) for the deeper portion.

### Step 7: Write the Layer Data Header and Rows

```
@  SLB  SLMH  SLLL  SDUL  SSAT  SRGF  SSKS  SBDM  SLOC  SLCL  SLSI  SLCF  SLNI  SLHW  SLHB  SCEC  SADC
     5   -99 0.228 0.385 0.481 1.000   -99  1.30  1.75  50.0  45.0   0.0 0.170   6.5   -99   -99   -99
    15   -99 0.228 0.385 0.481 1.000   -99  1.30  1.75  50.0  45.0   0.0 0.170   6.5   -99   -99   -99
    30   -99 0.249 0.406 0.482 0.638   -99  1.30  1.60  50.0  45.0   0.0 0.170   6.5   -99   -99   -99
```

**Layer parameter definitions**:

| Parameter | Width | Units | Description | Required | Typical Range |
|-----------|-------|-------|-------------|----------|---------------|
| SLB | 6 | cm | Layer bottom depth | YES | 5-300 |
| SLMH | 6 | code | Master horizon (A, B, C, etc.) | No (-99) | -99, A, AP, B, etc. |
| SLLL | 6 | cm3/cm3 | Lower limit of plant-available water (wilting point) | YES | 0.02-0.35 |
| SDUL | 6 | cm3/cm3 | Drained upper limit (field capacity) | YES | 0.10-0.50 |
| SSAT | 6 | cm3/cm3 | Saturated water content | YES | 0.30-0.60 |
| SRGF | 6 | 0-1 | Root growth factor (relative root density) | YES | 0.0-1.0 |
| SSKS | 6 | cm/hr | Saturated hydraulic conductivity | No (-99) | 0.01-50.0 |
| SBDM | 6 | g/cm3 | Bulk density (moist) | YES | 0.90-1.80 |
| SLOC | 6 | % | Organic carbon (% by weight) | YES | 0.01-10.0 |
| SLCL | 6 | % | Clay content (% by weight) | Recommended | 0-100 |
| SLSI | 6 | % | Silt content (% by weight) | Recommended | 0-100 |
| SLCF | 6 | % | Coarse fragment content (% by volume) | No | 0-80 |
| SLNI | 6 | % | Total nitrogen (% by weight) | Recommended | 0.001-1.0 |
| SLHW | 6 | -- | Soil pH in water | Recommended | 3.5-9.5 |
| SLHB | 6 | -- | Soil pH in buffer | No (-99) | -99 |
| SCEC | 6 | cmol/kg | Cation exchange capacity | No (-99) | 1-60 |
| SADC | 6 | -- | Additional category/code | No (-99) | -99 |

### Step 8: Enforce Water Limit Ordering

For every layer, the following constraint must hold:

```
SLLL < SDUL < SSAT
```

**Minimum gap enforcement**: DSSAT requires a minimum gap of 0.01 cm3/cm3 between consecutive limits:
- `SDUL - SLLL >= 0.01`
- `SSAT - SDUL >= 0.01`

**Validation procedure for each layer**:
1. Check: `SLLL >= 0.0` (lower limit cannot be negative)
2. Check: `SDUL > SLLL` (if equal, add 0.01 to SDUL)
3. Check: `SSAT > SDUL` (if equal, add 0.01 to SSAT)
4. Check: `SSAT <= 1.0 - (SBDM / 2.65)` approximately (SSAT cannot exceed porosity; particle density ~ 2.65 g/cm3)

**Failure mode**: If water limits are inverted (e.g., SLLL > SDUL), DSSAT will compute negative available water, causing division-by-zero or negative soil water content, which crashes the simulation.

### Step 9: Compute Root Growth Factor (SRGF)

SRGF controls the relative root density distribution. It ranges from 0 (no roots) to 1 (maximum root presence).

**Default calculation** (from DSSAT documentation):
```
For SLB <= 15 cm: SRGF = 1.000
For SLB > 15 cm:  SRGF = 1.0 * EXP(-0.02 * layer_center)
                   where layer_center = (SLB_previous + SLB_current) / 2
```

**Example**:
| SLB (cm) | Layer Center (cm) | SRGF |
|----------|-------------------|------|
| 5 | 2.5 | 1.000 |
| 15 | 10.0 | 1.000 |
| 30 | 22.5 | 0.638 |
| 45 | 37.5 | 0.472 |
| 60 | 52.5 | 0.350 |
| 90 | 75.0 | 0.223 |
| 120 | 105.0 | 0.122 |
| 150 | 135.0 | 0.067 |
| 180 | 165.0 | 0.037 |
| 210 | 195.0 | 0.020 |

**Decision rule**: If you have measured root distribution data, use those values directly. If not, use the exponential decay function above. For shallow-rooted crops (e.g., rice), you may want steeper decay (larger coefficient). For deep-rooted crops (e.g., sugarcane), use shallower decay.

### Step 10: Use Pedotransfer Functions When Hydraulic Data Is Unavailable

If measured SLLL, SDUL, and SSAT are not available, estimate them from texture data using pedotransfer functions.

**Saxton et al. (1986) method** (used by DSSAT's built-in estimation):

From clay (SLCL) and sand (100 - SLCL - SLSI) percentages:
```
SLLL = f(clay%, sand%)  -- wilting point at -1500 kPa
SDUL = f(clay%, sand%)  -- field capacity at -33 kPa
SSAT = f(porosity)      -- based on bulk density
```

**Reference ranges by texture class** (from SOIL.SOL header comments):

| Texture | SLLL Range | SDUL Range | SSAT Range |
|---------|-----------|-----------|-----------|
| C (Clay) | 0.220-0.346 | 0.330-0.467 | 0.413-0.488 |
| CL (Clay Loam) | 0.156-0.218 | 0.282-0.374 | 0.417-0.512 |
| L (Loam) | 0.083-0.156 | 0.222-0.312 | 0.415-0.501 |
| LS (Loamy Sand) | 0.059-0.110 | 0.137-0.185 | 0.355-0.416 |
| S (Sand) | 0.055-0.085 | 0.123-0.158 | 0.374-0.400 |
| SC (Sandy Clay) | 0.195-0.294 | 0.276-0.389 | 0.376-0.409 |
| SCL (Sandy Clay Loam) | 0.132-0.191 | 0.213-0.304 | 0.360-0.418 |
| SI (Silt) | 0.096-0.099 | 0.299-0.307 | 0.442-0.488 |
| SIC (Silty Clay) | 0.224-0.326 | 0.379-0.456 | 0.455-0.489 |
| SICL (Silty Clay Loam) | 0.155-0.219 | 0.324-0.392 | 0.448-0.511 |
| SIL (Silt Loam) | 0.082-0.152 | 0.240-0.333 | 0.439-0.547 |
| SL (Sandy Loam) | 0.066-0.133 | 0.164-0.243 | 0.348-0.499 |

**Bulk density estimation** (if not measured):
```
SBDM = 100 / (SOM% / 0.224 + (100 - SOM%) / mineral_BD)
where SOM% = SLOC * 1.724 (van Bemmelen factor)
and mineral_BD depends on texture (typically 1.4-1.7 g/cm3)
```

### Step 11: Handle MESOL Options for Layer Redistribution

The MESOL switch in *SIMULATION CONTROLS affects how the model handles soil layers:

| MESOL Value | Behavior |
|-------------|----------|
| 1 | Original layer structure used as-is from .SOL file |
| 2 | New default: model may redistribute layers for numerical stability (DSSAT v4.8+ default) |
| 3 | User-defined layer structure with additional constraints |

**Decision rule**: Use MESOL=2 (default) for most applications. Use MESOL=1 only if you require exact layer boundaries to match specific measurement depths. Use MESOL=3 only if you have explicit layer definitions that must be preserved.

### Step 12: Validate the Complete Soil Profile

**Tool reference**: `validate_soil_profile` -- invoke this tool with the .SOL file path and pedon code to run automated validation.

Manual validation checklist:

1. **Layer depth monotonicity**: Each SLB value is strictly greater than the previous.
2. **Water limit ordering**: SLLL < SDUL < SSAT for every layer.
3. **Minimum gap**: SDUL - SLLL >= 0.01 and SSAT - SDUL >= 0.01 for every layer.
4. **Bulk density plausibility**: 0.8 <= SBDM <= 2.0 for all layers.
5. **Organic carbon profile**: SLOC should decrease with depth (typical). Surface SLOC is highest.
6. **SRGF profile**: SRGF should decrease with depth. Surface layer SRGF = 1.0.
7. **Texture consistency**: SLCL + SLSI <= 100 for every layer. Sand = 100 - SLCL - SLSI.
8. **Profile depth**: Total depth (last SLB) >= 20 cm. Profiles < 20 cm may cause division-by-zero.
9. **Layer count**: Number of layers <= 20. Profiles with > 20 layers will be silently truncated.
10. **Pedon code uniqueness**: No other profile in the .SOL file has the same 10-character pedon code.

## Expected Outputs

| Output | Format | Verification |
|--------|--------|--------------|
| Updated .SOL file | Multiple profiles, each starting with `*` | File parses without error |
| New profile entry | 10-char pedon code header + surface params + layer data | Profile found by ID_SOIL search |
| Layer data | 1-20 rows of soil properties | Water limits ordered, depths monotonic |
| Metadata | Site line with LAT, LONG | Present and populated |

## Validation Checks

1. **REQUIRED**: Profile header starts with `*` and contains a 10-character pedon code.
2. **REQUIRED**: Surface parameter line contains SALB, SLU1, SLDR, SLRO, SLNF, SLPF.
3. **REQUIRED**: Layer data header (@SLB...) is present.
4. **REQUIRED**: At least 1 layer of data is present.
5. **REQUIRED**: SLLL < SDUL < SSAT for every layer (with 0.01 minimum gap).
6. **REQUIRED**: SLB values are monotonically increasing.
7. **REQUIRED**: SBDM, SLOC, SLLL, SDUL, SSAT are not -99 for any layer.
8. **REQUIRED**: Layer count <= 20.
9. **RECOMMENDED**: First layer SLB <= 5 cm.
10. **RECOMMENDED**: Total profile depth >= 20 cm.

## Common Pitfalls

1. **Layer depths not monotonic**: Setting layer bottom depths out of order (e.g., 30, 15, 60) causes the soil water balance to fail immediately. Always list layers in ascending order of SLB.

2. **Water limits inverted**: Setting SLLL > SDUL or SDUL > SSAT produces negative available water. This can cause the model to crash or produce physically impossible results (negative soil water content). Always verify the strict ordering SLLL < SDUL < SSAT.

3. **Shallow soil < 20 cm causing division-by-zero**: DSSAT calculates average soil properties over the profile depth. Very shallow soils (total depth < 20 cm) can trigger division-by-zero in layer-averaging routines. This was specifically identified and patched in recent DSSAT commits (commit d3a65881: "Prevent zero divide for shallow soils less than 20 cm"), but the safest practice is to use profiles >= 20 cm deep.

4. **More than 20 layers silently truncated**: If you define more than 20 layers, DSSAT will only use the first 20 without issuing any warning. Layers 21+ will be silently ignored, effectively cutting off the bottom of your soil profile. Always check: count the number of data rows under `@SLB` and ensure it is <= 20.

5. **Top layer > 5 cm causing instability**: If the first layer is thick (e.g., 0-20 cm), the surface energy balance calculations become numerically unstable, producing unrealistic evaporation rates and soil temperature swings. Always use a 5-cm first layer.

6. **SLOC = 0 in surface layer**: Zero organic carbon is unrealistic for agricultural soils and will cause zero N mineralization potential. Even desert soils have trace organic carbon. Use a minimum of 0.01%.

7. **Missing SBDM (bulk density)**: If SBDM is -99, the model cannot compute water storage volumes. SBDM is a critical input; estimate it from texture if not measured.

8. **SRGF = 0 in all layers**: If root growth factor is zero everywhere, the crop cannot extract water or nutrients from any layer and will die immediately. Ensure at least the surface layers have SRGF > 0.

9. **Duplicate pedon codes in .SOL file**: If two profiles share the same 10-character code, DSSAT will use the first one found and ignore the second. Ensure uniqueness.

10. **Adding a new profile without preserving existing ones**: When editing a .SOL file, always append the new profile below existing profiles. Do not overwrite the file or delete other profiles unless intentional.
