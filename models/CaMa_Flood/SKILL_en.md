---
name: cama-flood-integration
description: VIC-CaMa-Flood model coupling assistant. Used to couple VIC hydrological model output with the CaMa-Flood river routing model, including regionalization, data conversion, and model execution
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
---

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



# VIC-CaMa-Flood Model Coupling Assistant

You are a professional hydrological model coupling assistant, helping users integrate VIC model output with the CaMa-Flood river routing model.

## CaMa-Flood Model Overview

CaMa-Flood (Catchment-based Macro-scale Floodplain) is a global-scale river routing and flood inundation model used to simulate river water levels, discharge, and flood inundation extent.

### Model Features
- Catchment-based river routing model
- Simulates river channel flow and floodplain inundation
- Supports multiple resolutions (15min, 3sec, 1min, etc.)
- Can be coupled with land surface models (VIC, MATSIRO, etc.)

## Model Coupling Workflow

```
VIC model output → Data format conversion → CaMa-Flood map preparation (3 steps) → CaMa-Flood execution → Discharge/water level output

Step 1: VIC run
  └─ Output: huaihe_fluxes_*.txt (gridded text files)
  └─ Variables: OUT_RUNOFF, OUT_BASEFLOW

Step 2: VIC post-processing
  └─ Script: scripts/vic_post/process_data_windows_ymd.py
  └─ Output: runoff_YYYY.nc (NetCDF format)
  └─ Location: outputs/{basin}/cama_input/

Step 3: CaMa-Flood map preparation (⚠️ Must be executed)
  ├─ 3.1 Regionalization: Clip basin from global map
  │   └─ Tools: src_region/cut_domain, combine_hires
  ├─ 3.2 Generate input matrix: VIC grid → CaMa grid mapping
  │   └─ Tools: src_param/generate_inpmat
  └─ 3.3 Generate channel parameters: Based on runoff climatology
      └─ Tools: src_param/calc_outclm, calc_rivwth

Step 4: CaMa-Flood execution
  ├─ NC format: Full variable output (outflw, rivdph, sfcelv, flddph, fldfrc, rivsto)
  └─ BIN format: flddph output only (for downscaling)
```

## Workspace Structure

```
hydro-model-workspace/
├── outputs/vic_result/         # VIC model output
│   └── huaihe_fluxes_*.txt     # 224 grid point files
├── scripts/vic_post/           # VIC post-processing scripts
│   └── process_data_windows_ymd.py
└── model/cmf_v420_pkg/         # CaMa-Flood model
    ├── src/                    # Source code
    │   └── MAIN_cmf            # Executable (compiled)
    ├── map/                    # Map files
    │   ├── glb_15min/          # Global 15-minute map
    │   ├── huaihe_15min/       # Huaihe regional map
    │   └── bengbu_15min/       # Bengbu regional map (to be generated)
    ├── inp/                    # Input data
    │   └── bengbu/             # Bengbu runoff input (to be generated)
    ├── out/                    # Output results
    │   └── bengbu_*/           # Bengbu simulation results
    └── gosh/                   # Run scripts
        └── run_bengbu_1d.sh    # Bengbu run script (to be created)
```

## Key Configuration Parameters

### Basin Boundaries (bengbu)

Automatically obtained from shapefile:
- **West**: 111.75° (extended westward by 0.25° for grid alignment)
- **East**: 117.75° (extended eastward by 0.25° for grid alignment)
- **South**: 31.0°
- **North**: 35.0°
- **Grid Size**: 0.25° (consistent with VIC)

### Grid Dimensions

- **NX** (east-west): 24 grid points ((117.75-111.75)/0.25)
- **NY** (north-south): 16 grid points ((35.0-31.0)/0.25)
- **Total**: 384 grid points (covering the domain, including areas outside the basin)

### Time Configuration

- **Simulation period**: 2023-01-01 to 2024-12-31
- **Time step**: 86400 seconds (daily)
- **Input frequency**: 24 hours (IFRQ_INP = 24)
- **Output frequency**: 24 hours (IFRQ_OUT = 24)

## ⚠️ Critical Prerequisites

### VIC Simulation Must Be Completed
Before running CaMa-Flood, VIC simulation must be completed and NetCDF-format runoff data must be generated. See the `vic-auto-run` skill.

### ⚠️ Maps Must Be Re-generated (Cannot Be Reused) **[Critical Step]**

**🚨 Serious Warning**: For each new basin, the complete three-step map preparation **must** be re-executed. You **must never** directly use existing folders under the map directory (such as manual_bengbu, etc.).

**Why reuse is not possible**:
- Different basins have different latitude/longitude extents
- River network topologies differ
- VIC grid to CaMa grid mapping relationships differ
- Direct reuse will cause path errors and simulation failures

**Correct workflow**:
1. **Create a new directory**: `mkdir map/{basin}_15min/` (not manual_{basin})
2. **Execute three steps**: Regionalization → Input matrix → Channel parameters
3. **Verify files**: Ensure all .bin files and diminfo files have been generated
4. **Use correct paths**: Use `map/{basin}_15min/` in run scripts, not `map/manual_{basin}/`

## Core Tasks

### Task 0: Create a New Map Directory (⚠️ Must Be Executed)

**Purpose**: Create a dedicated map parameter folder for the new basin.

```bash
cd /Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map
mkdir {basin}_15min
```

**Example**: For the Bengbu basin, create the `bengbu_15min` directory.

### Task 1: VIC Output Post-processing

**Script**: `scripts/vic_post/process_{basin}.py` (one script per basin, e.g., process_bengbu.py)

**Functionality**:
- Read VIC gridded text files (huaihe_fluxes_*.txt)
- Extract runoff data (OUT_RUNOFF + OUT_BASEFLOW)
- Convert to CaMa-Flood NetCDF format

**🔴 Key Modifications**:
```python
# Input path - must point to the correct basin VIC output directory
INPUT_DIR = "/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/vic_result"

# Output path - placed uniformly in the basin's cama_input directory
OUTPUT_DIR = "/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_input"

# Time range
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"

# Grid definition (adjust according to the basin)
NX = 24
NY = 16
WEST = 111.875   # Center longitude of the first grid point
EAST = 117.625   # Center longitude of the last grid point
NORTH = 34.875   # Center latitude of the first grid point
SOUTH = 31.125   # Center latitude of the last grid point
GRID_SIZE = 0.25

# File name prefix
FILE_PREFIX = "huaihe_fluxes_"
OUTPUT_NC_PREFIX = "{basin}_runoff_1d_"  # 🔴 Output file name format: {basin}_runoff_1d_YYYY.nc
```

**🔴 Output File Naming**: `{basin}_runoff_1d_YYYY.nc` (e.g., `bengbu_runoff_1d_2024.nc`). The CROFCDF path in the CaMa run script must match this.

### Task 2: CaMa-Flood Map Preparation (Three-Step Workflow)

**⚠️ Critical**: These three steps must be completed in order, and must be re-executed for each new basin.

#### Step 2.1: Regionalization (Clip Global Map)

**Directory**: `model/cmf_v420_pkg/map/{basin}_15min/src_region/`

**Steps**:

1. **Copy regionalization tools**:
   ```bash
   cd model/cmf_v420_pkg/map/{basin}_15min
   cp -r ../huaihe_15min/src_region ./src_region
   cd src_region
   ```

2. **🔴 Compile regionalization programs** (must be done for cross-platform compatibility):
   ```bash
   make clean
   make all
   ```
   **Note**: Binary files are platform-dependent. Executables copied from other directories cannot run directly and must be recompiled.

3. **Create s01-regional_map.sh** (modify latitude/longitude extent for the basin):
   ```bash
   #!/bin/sh

   # Modify the following parameters to match the actual basin extent
   SOURCE="../../glb_15min/"
   WEST="111.75"   # West boundary (degrees)
   EAST="117.75"   # East boundary (degrees)
   SOUTH="31.0"    # South boundary (degrees)
   NORTH="35.0"    # North boundary (degrees)

   echo "$SOURCE" > region_info.txt
   echo "$WEST" >> region_info.txt
   echo "$EAST" >> region_info.txt
   echo "$SOUTH" >> region_info.txt
   echo "$NORTH" >> region_info.txt

   ./cut_domain
   ./cut_bifway
   ./set_map

   # Generate high-resolution data (for downscaling)
   HDIRS="1min 30sec 15sec 3sec"
   for HIRES in $HDIRS
   do
     if [ -f $SOURCE/$HIRES/location.txt ]; then
       echo "Processing high-resolution data: $HIRES"
       mkdir -p ../$HIRES
       ./combine_hires $HIRES
     fi
   done

   ./s02-wrte_ctl_map.sh
   ```

4. **Run regionalization**:
   ```bash
   chmod +x s01-regional_map.sh
   ./s01-regional_map.sh
   ```

**Output files** (generated in `../{basin}_15min/`):
- nextxy.bin - Flow direction data
- ctmare.bin - Catchment area
- elevtn.bin - Elevation
- nxtdst.bin - Distance to downstream grid point
- rivlen.bin - River channel length
- fldhgt.bin - Floodplain height
- width.bin - Default channel width
- 1min/ - High-resolution data (for downscaling)

#### Step 2.2: Generate Input Matrix (VIC → CaMa Mapping)

**⚠️ Dependency**: Step 2.1 (regionalization) must be completed first.

**Directory**: `model/cmf_v420_pkg/map/{basin}_15min/src_param/`

**Steps**:

1. **Copy src_param tools**:
   ```bash
   cd model/cmf_v420_pkg/map/{basin}_15min
   cp -r ../glb_15min/src_param ./src_param
   cd src_param
   ```

2. **🔴 Compile** (must be done for cross-platform compatibility):
   ```bash
   make clean
   make all
   ```
   **Note**: Must be recompiled on the local machine. Binary files compiled on other platforms cannot be used.

3. **Create s02-generate_inpmat.sh** (modify parameters according to VIC grid):
   ```bash
   #!/bin/sh
   cd ..

   # Configuration parameters (modify according to actual VIC grid)
   DIMINFO="diminfo_{basin}_025deg.txt"
   INPMAT="inpmat_{basin}_025deg.bin"

   # VIC runoff data grid information
   GRSIZEIN=0.25       # VIC grid size
   WESTIN=111.75       # VIC domain west boundary
   EASTIN=117.75       # VIC domain east boundary
   NORTHIN=35.0        # VIC domain north boundary
   SOUTHIN=31.0        # VIC domain south boundary
   OLAT="NtoS"         # Latitude order: North to South

   TAG="1min"          # High-resolution data directory

   # Generate input matrix
   ./src_param/generate_inpmat $TAG $GRSIZEIN $WESTIN $EASTIN $NORTHIN $SOUTHIN $OLAT $DIMINFO $INPMAT
   ```

4. **Run**:
   ```bash
   chmod +x s02-generate_inpmat.sh
   ./s02-generate_inpmat.sh
   ```

**Output files**:
- diminfo_{basin}_025deg.txt - Grid dimension information
- inpmat_{basin}_025deg.bin - Input mapping matrix

#### Step 2.3: Generate Channel Parameters

**⚠️ Dependency**: Steps 2.1 and 2.2 must be completed first.

**⚠️ Important**: The correct runoff climatology data path must be used:
`/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map/data/ELSE_GPCC_coastmod_dayclm-1981-2010.one`

**Directory**: `model/cmf_v420_pkg/map/{basin}_15min/src_param/`

**Steps**:

1. **Create s01-channel_params.sh**:
   ```bash
   #!/bin/sh
   cd ..

   TYPE='bin'
   INTERP='inpmat'
   DIMINFO='./diminfo_{basin}_025deg.txt'
   CROFBIN="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map/data/ELSE_GPCC_coastmod_dayclm-1981-2010.one"

   # Calculate annual mean discharge
   ./src_param/calc_outclm $TYPE $INTERP $DIMINFO $CROFBIN

   # Channel parameters
   HC=0.1; HP=0.50; HO=0.00; HMIN=1.0
   WC=2.50; WP=0.60; WO=0.00; WMIN=5.0

   # Calculate channel width and depth
   ./src_param/calc_rivwth $TYPE $DIMINFO $HC $HP $HO $HMIN $WC $WP $WO $WMIN

   # Generate GWDLR and roughness
   cp rivwth.bin rivwth_gwdlr.bin
   python3 -c "
   import numpy as np
   data = np.fromfile('rivwth.bin', dtype='float32')
   data[:] = 0.03
   data.tofile('rivman.bin')
   "
   ```

2. **Run**:
   ```bash
   chmod +x s01-channel_params.sh
   ./s01-channel_params.sh
   ```

**Output files**:
- rivwth.bin, rivhgt.bin - Channel width and depth
- rivwth_gwdlr.bin - GWDLR channel width
- rivman.bin - Channel roughness (default 0.03)

### Task 3: Create CaMa-Flood Run Script

**⚠️ Key Differences**:
- **NC format**: For routine analysis, outputs multiple variables (outflw, rivdph, sfcelv, flddph, etc.)
- **BIN format**: For downscaling only, outputs only the flddph variable

**⚠️ Path Note**: Absolute paths must be used. Avoid `../` relative paths (which cause STOP 10 errors).

**⚠️ LINTERP Setting**:
- If the VIC grid exactly matches the CaMa grid, set `LINTERP=.FALSE.` and `CINPMAT=''`
- If interpolation mapping is needed, set `LINTERP=.TRUE.` and `CINPMAT='...inpmat_{basin}_025deg.bin'`
- **Recommended**: Use `LINTERP=.FALSE.` (more stable, avoids interpolation errors)

#### 3.1 NC Format Run Script

**File**: `model/cmf_v420_pkg/gosh/run_{basin}_nc.sh`

**Configuration**:

```bash
#!/bin/sh

# --- 1. Basic Settings ---
BASE="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg"
export OMP_NUM_THREADS=8
cd ${BASE}

# --- 2. Experiment Definition ---
EXP="bengbu_2024_nc"
RDIR="/Volumes/Expansion2t/hydro-model-workspace/outputs/bengbu/cama_nc"
PROG=${BASE}/src/MAIN_cmf
NMLIST="./input_cmf.nam"

YSTA=2023
YEND=2024
SPINUP=0
NSP=1  # Number of spin-up cycles

# --- 3. Prepare Run Directory ---
mkdir -p ${RDIR}
cd ${RDIR}

if [ ${SPINUP} -eq 0 ]; then
  echo "--- New run, cleaning directory: ${RDIR} ---"
  rm -rf ./*
else
  NSP=0
fi

# --- 4. Annual Loop ---
ISP=1
IYR=${YSTA}
while [ ${IYR} -le ${YEND} ];
do
  echo ""
  echo "##################################################"
  echo "--- Processing Year: ${IYR} (Spin-up: ${ISP}) ---"
  echo "##################################################"

  CYR=`printf %04d ${IYR}`
  EYR=`expr ${IYR} + 1`

  if [ ${IYR} -eq ${YSTA} ] && [ ${SPINUP} -eq 0 ]; then
    LRESTART=".FALSE."
    CRESTSTO="''"
  else
    LRESTART=".TRUE."
    CRESTSTO="'./restart${CYR}010100.nc'"
  fi

  ln -sf $PROG ./MAIN_cmf

  # --- 5. Create Configuration File for Current Year ---
  cat > ${NMLIST} << EOF
  &NRUNVER
  LADPSTP  = .TRUE.
  LPTHOUT  = .FALSE.
  LRESTART = ${LRESTART}
  /
  &NDIMTIME
  CDIMINFO = '../../map/bengbu_15min/diminfo_bengbu_025deg.txt'
  DT       = 86400
  IFRQ_INP = 24
  /
  &NPARAM
  PMANRIV  = 0.03D0
  PMANFLD  = 0.10D0
  PCADP    = 0.7
  PDSTMTH  = 10000.D0
  /
  &NSIMTIME
  SYEAR = ${IYR}
  SMON  = 1
  SDAY  = 1
  SHOUR = 0
  EYEAR = ${EYR}
  EMON  = 1
  EDAY  = 1
  EHOUR = 0
  /
  &NMAP
  LMAPCDF  = .FALSE.
  CNEXTXY  = '../../map/bengbu_15min/nextxy.bin'
  CGRAREA  = '../../map/bengbu_15min/ctmare.bin'
  CELEVTN  = '../../map/bengbu_15min/elevtn.bin'
  CNXTDST  = '../../map/bengbu_15min/nxtdst.bin'
  CRIVLEN  = '../../map/bengbu_15min/rivlen.bin'
  CFLDHGT  = '../../map/bengbu_15min/fldhgt.bin'
  CRIVWTH  = '../../map/bengbu_15min/rivwth_gwdlr.bin'
  CRIVHGT  = '../../map/bengbu_15min/rivhgt.bin'
  CRIVMAN  = '../../map/bengbu_15min/rivman.bin'
  /
  &NRESTART
  CRESTSTO = ${CRESTSTO}
  CRESTDIR = './'
  CVNREST  = 'restart'
  LRESTCDF = .TRUE.
  IFRQ_RST = 0
  /
  &NFORCE
  LINPCDF  = .TRUE.
  LINTERP  = .TRUE.
  CINPMAT  = '../../map/bengbu_15min/inpmat_bengbu_025deg.bin'
  CROFCDF  = '/Volumes/Expansion2t/hydro-model-workspace/outputs/bengbu/cama_input/bengbu_runoff_1d_${CYR}.nc'
  CVNROF   = 'Runoff'
  SYEARIN  = ${IYR}
  SMONIN   = 1
  SDAYIN   = 1
  SHOURIN  = 0
  /
  &NOUTPUT
  COUTDIR  = './'
  CVARSOUT = 'outflw,rivdph,sfcelv,flddph,fldfrc,rivsto'
  COUTTAG  = '${CYR}'
  LOUTCDF  = .TRUE.
  NDLEVEL  = 0
  IFRQ_OUT = 24
  /
  &NBOUND
  /
  &NDAMOUT
  /
  &NLEVEE
  /
EOF

  # --- 6. Execute Model ---
  echo "Running CaMa-Flood for year ${IYR}..."
  time ./MAIN_cmf

  # --- 7. Spin-up Handling ---
  if [ ${IYR} -eq ${YSTA} ] && [ ${ISP} -le ${NSP} ]; then
    SPINUP=1
    IYR1=`expr ${IYR} + 1`
    CYR1=`printf %04d ${IYR1}`
    mv ./restart${CYR1}010100.nc ./restart${CYR}010100.nc 2>/dev/null
    mkdir -p spinup-${ISP}
    mv ./*${CYR}.nc spinup-${ISP}/ 2>/dev/null
    ISP=`expr ${ISP} + 1`
  else
    IYR=`expr ${IYR} + 1`
  fi
done

echo "--- All simulations finished! ---"
echo "Results saved in: ${RDIR}"
```

**Key Configuration**:
- `LINTERP = .FALSE.` - No interpolation (recommended, more stable)
- `CINPMAT = ''` - No input matrix
- `CROFCDF` - Use **absolute path**
- `CVARSOUT` - NC format outputs multiple variables

#### 3.2 BIN Format Run Script (For Downscaling)

**File**: `model/cmf_v420_pkg/gosh/run_{basin}_bin.sh`

**Differences**: Only two modifications needed
1. `LOUTCDF = .FALSE.` - Output in BIN format
2. `CVARSOUT = 'flddph'` - Output flood inundation depth only

```bash
#!/bin/sh

BASE="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg"
export OMP_NUM_THREADS=8

EXP="{basin}_YYYY_bin"
RDIR="/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_bin"
# ... (other configurations same as NC format) ...

cat > ${NMLIST} << EOFN
  # ... (preceding configurations same as NC format) ...
  &NOUTPUT
  COUTDIR  = './'
  CVARSOUT = 'flddph'
  COUTTAG  = '${CYR}'
  LOUTCDF  = .FALSE.   # ⚠️ BIN format
  NDLEVEL  = 0
  IFRQ_OUT = 24
  /
  # ... (following configurations same as NC format) ...
EOFN

echo "Running CaMa-Flood BIN format..."
time ./MAIN_cmf

echo "Results saved in: ${RDIR}"
ls -lh ${RDIR}/*.bin
```

### Task 4: Complete Run Workflow (New Basin)

**🤖 Automated Check (Recommended)**:

Before running CaMa-Flood, use the automated check script to verify all prerequisites:

```bash
cd /Volumes/Expansion2t/hydro-model-workspace/skills/cama-flood-integration
./check_prerequisites.sh bengbu 2024
```

The script will automatically check:
- VIC output files
- NetCDF runoff data
- CaMa map files (most error-prone)
- Channel parameters
- Input matrix
- 1min high-resolution data

If all checks pass, it will display `✅ All checks passed! Ready to run CaMa-Flood simulation`

---

**🔍 Manual Checklist** (if not using the automated script):

#### VIC-Related
- [ ] VIC model ran successfully (no errors)
- [ ] VIC post-processing generated `outputs/{basin}/cama_input/{basin}_runoff_1d_YYYY.nc`
- [ ] Verify NetCDF file size is reasonable (>100KB)
- [ ] Check that the variable name is 'Runoff' and the unit is 'mm/day'

#### CaMa Map Preparation (🚨 Most Error-Prone)
- [ ] **New map directory created** `map/{basin}_15min/` (not manual_{basin})
- [ ] **Step 2.1 (regionalization) completed**: Check that `nextxy.bin`, `ctmare.bin`, etc. exist
- [ ] **Step 2.2 (input matrix) completed**: Check that `diminfo_{basin}_025deg.txt` and `inpmat_{basin}_025deg.bin` exist
- [ ] **Step 2.3 (channel parameters) completed**: Check that `rivwth.bin`, `rivhgt.bin`, `rivman.bin` exist
- [ ] **1min directory generated**: Check that `map/{basin}_15min/1min/` exists (for downscaling)

#### Run Script Configuration
- [ ] **Absolute paths** used in run scripts (avoid relative path errors)
- [ ] All map file paths point to `map/{basin}_15min/` (not manual_{basin})
- [ ] Runoff data path is correct (absolute path)

**Step 1: VIC Post-processing** (see vic-auto-run skill)
```bash
cd scripts/vic_post
source /Users/yc/Desktop/project/python_env/bin/activate
python3 process_data_windows_ymd.py
```

**Expected Output**:
- `outputs/{basin}/cama_input/runoff_YYYY.nc`

**Step 2: Map Preparation Three Steps** (⚠️ Must be executed for each new basin)

2.1 Regionalization:
```bash
cd model/cmf_v420_pkg/map/{basin}_15min/src_region
./s01-regional_map.sh
```

2.2 Generate input matrix:
```bash
cd ../src_param
./s02-generate_inpmat.sh
```

2.3 Generate channel parameters:
```bash
./s01-channel_params.sh
```

**Expected Output**:
- Map files: nextxy.bin, ctmare.bin, elevtn.bin, nxtdst.bin, rivlen.bin, fldhgt.bin
- Channel parameters: rivwth_gwdlr.bin, rivhgt.bin, rivman.bin
- Mapping files: diminfo_{basin}_025deg.txt, inpmat_{basin}_025deg.bin
- High-resolution: 1min/ directory

**Step 3: Run CaMa-Flood**

3.1 NC format (full variables):
```bash
cd /Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/gosh
./run_{basin}_nc.sh
```

**Expected Output** (in `outputs/{basin}/cama_nc/`):
- o_outflw{YYYY}.nc - River discharge
- o_rivdph{YYYY}.nc - River water depth
- o_sfcelv{YYYY}.nc - Water surface elevation
- o_flddph{YYYY}.nc - Floodplain water depth
- o_fldfrc{YYYY}.nc - Floodplain area fraction
- o_rivsto{YYYY}.nc - River storage

3.2 BIN format (for downscaling):
```bash
./run_{basin}_bin.sh
```

**Expected Output** (in `outputs/{basin}/cama_bin/`):
- flddph{YYYY}.bin - Flood inundation depth (BIN format)

**🔴 Downscaling Preparation**: The downscaling script expects the bin file in `model/cmf_v420_pkg/out/{basin}_{YYYY}_bin/` directory. A symbolic link needs to be created:
```bash
mkdir -p model/cmf_v420_pkg/out/{basin}_{YYYY}_bin
ln -sf /Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_bin/flddph{YYYY}.bin \
       model/cmf_v420_pkg/out/{basin}_{YYYY}_bin/flddph{YYYY}.bin
```

## Output Variable Description

### CaMa-Flood Output Variables

| Variable | Unit | Description |
|----------|------|-------------|
| outflw | m³/s | River channel outflow discharge |
| rivdph | m | River channel water depth |
| sfcelv | m | Water surface elevation (relative to sea level) |
| flddph | m | Floodplain water depth |
| fldfrc | - | Floodplain inundation area fraction (0-1) |
| rivsto | m³ | River channel storage |
| fldsto | m³ | Floodplain storage |
| fldare | m² | Floodplain inundation area |

## Common Parameter Description

### Model Parameters

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| Channel roughness | PMANRIV | 0.03 | Manning coefficient (channel) |
| Floodplain roughness | PMANFLD | 0.10 | Manning coefficient (floodplain) |
| Adaptive time step | PCADP | 0.7 | CFL condition coefficient |
| Diffusion distance | PDSTMTH | 10000 | Diffusion method distance threshold (m) |

### Time Settings

- **DT**: Base time step (seconds)
- **IFRQ_INP**: Input data frequency (hours)
- **IFRQ_OUT**: Output data frequency (hours)
- **IFRQ_RST**: Restart file output frequency (hours, 0=disabled)

## Error Handling

### Issue 1: STOP 10 Error

**Symptom**: CaMa exits immediately, displaying `STOP 10`

**Cause**: NetCDF file read error, usually caused by:
1. Incorrect runoff data file path (using relative path `../`)
2. Runoff data file does not exist
3. Incorrect LINTERP interpolation configuration

**Solution**:
```bash
# 1. Check if the runoff file exists
ls /Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_input/{basin}_runoff_1d_YYYY.nc

# 2. Use absolute path (do not use ../)
CROFCDF = '/Volumes/Expansion2t/hydro-model-workspace/outputs/{basin}/cama_input/{basin}_runoff_1d_${CYR}.nc'

# 3. Use LINTERP=.FALSE. (recommended)
LINTERP = .FALSE.
CINPMAT = ''

# 4. View detailed log
tail -50 log_CaMa.txt
```

### Issue 2: Missing Map Files

**Symptom**: `Error reading nextxy.bin` or other .bin file errors

**Cause**: Map preparation three-step workflow was not completed or failed

**Solution**:
```bash
# Check if map files exist
cd model/cmf_v420_pkg/map/{basin}_15min
ls -lh *.bin

# Should contain the following files:
# nextxy.bin, ctmare.bin, elevtn.bin, nxtdst.bin, rivlen.bin, fldhgt.bin
# rivwth_gwdlr.bin, rivhgt.bin, rivman.bin

# If missing, re-run the three-step map preparation
```

### Issue 3: Incorrect Runoff Climatology Data Path

**Symptom**: `calc_outclm` fails, cannot find runoff data file

**Cause**: Incorrect CROFBIN path

**Solution**:
```bash
# Must use the correct absolute path
CROFBIN="/Volumes/Expansion2t/hydro-model-workspace/model/cmf_v420_pkg/map/data/ELSE_GPCC_coastmod_dayclm-1981-2010.one"

# Check if the file exists
ls -lh $CROFBIN
```

### Issue 4: Missing High-Resolution Data (For Downscaling)

**Symptom**: `generate_inpmat` or downscaling reports error finding 1min/location.txt

**Cause**: High-resolution data was not generated during regionalization

**Solution**:
```bash
# Ensure s01-regional_map.sh includes the combine_hires step
# Check if the 1min directory exists
ls -lh model/cmf_v420_pkg/map/{basin}_15min/1min/

# If it does not exist, re-run s01-regional_map.sh (full version)
```

### Issue 5: Dimension Mismatch

**Symptom**: `Dimension mismatch` or incorrect grid count

**Cause**: Inconsistency between VIC grid and CaMa grid definitions

**Solution**:
- Verify NX, NY, WEST, EAST, NORTH, SOUTH in the VIC post-processing script
- Check grid dimensions in the diminfo file
- Ensure generate_inpmat uses boundaries consistent with VIC

## Verification Checklist

Pre-run checks:
- [ ] VIC model ran successfully with complete output files
- [ ] Python post-processing script paths are configured
- [ ] CaMa-Flood executable exists
- [ ] Regionalization script is prepared

Post-run verification:
- [ ] NetCDF input files generated (check variables and dimensions)
- [ ] Map files generated (*.bin, diminfo, inpmat)
- [ ] CaMa-Flood ran without errors
- [ ] Output NC files generated
- [ ] Discharge values are reasonable (outflw > 0)

## Usage Example

```bash
# Complete run workflow
cd /Volumes/Expansion2t/hydro-model-workspace

# 1. VIC post-processing
source /Users/yc/Desktop/project/python_env/bin/activate
python3 scripts/vic_post/process_data_windows_ymd.py

# 2. CaMa-Flood regionalization (first run)
cd model/cmf_v420_pkg/map/bengbu_15min/src_region
./s01-regional_map.sh

# 3. Run CaMa-Flood
cd ../../gosh
./run_bengbu_1d.sh

# 4. View results
cd ../out/bengbu_2023
ls -lh *.nc
```

## Important Notes

1. **Coordinate system**: Ensure VIC and CaMa-Flood use the same coordinate system
2. **Grid alignment**: Boundaries should be aligned with grid resolution (multiples of 0.25°)
3. **Data units**: VIC output is in mm/day, conversion is required
4. **Temporal consistency**: Ensure VIC and CaMa-Flood simulation periods are consistent
5. **Memory requirements**: Large basins may require more memory
6. **Spin-up**: For the first run, 1-2 spin-up cycles are recommended to stabilize initial conditions

## References

- CaMa-Flood official website: http://hydro.iis.u-tokyo.ac.jp/~yamadai/cama-flood/
- CaMa-Flood GitHub: https://github.com/global-hydrodynamics/CaMa-Flood_v4
- Manual: `model/cmf_v420_pkg/doc/Manual_CaMa-Flood_v420.docx`
