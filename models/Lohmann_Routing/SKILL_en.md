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

# VIC Routing Model User Guide

## Overview

This skill is used to run the VIC hydrological model's Routing module, converting VIC runoff results into river discharge.

## Key Paths

- **Routing executable (route_1.0)**: `/Volumes/Expansion4t/hydro-space2/model/route_1.0/src/rout`
- **Routing parameter generation script**: `/Volumes/Expansion4t/hydro-space2/skills/routing-run/s5_routing_param/run_build_routing_new.py`
- **Routing configuration directory**: `/Volumes/Expansion4t/hydro-space2/docs/rout/`
- **VIC result directory**: `/Volumes/Expansion4t/hydro-space2/outputs/{basin_name}/vic_result/`
- **VIC preprocessed directory**: `/Volumes/Expansion4t/hydro-space2/outputs/{basin_name}/vic_for_routing/`

---

## Automatic Routing Parameter Generation

### Usage

1. Copy `run_build_routing_new.py` to your working directory
2. Modify configuration parameters in the script:
   - `SOIL_PARAM_PATH`: VIC soil parameter file path
   - `DEM_PATH`: DEM file path
   - `BASIN_SHP`: Basin boundary shapefile path
   - `OUTPUT_DIR`: Output directory
   - `STATION_NAME`: Station name
   - `OUTLET_LON/LAT`: Outlet coordinates (optional, script will find max accumulation point)
3. Run the script: `python run_build_routing_new.py`

### Generated Files

| File | Description |
|------|-------------|
| XX_direc.txt | Flow direction file (D8 encoding) |
| XX_frac.txt | Area fraction file |
| XX_xmask.txt | Flow distance file |
| XX_staloc.txt | Station location file |
| UH.all | Unit hydrograph parameter file |
| rout_global.txt | Routing configuration file |

### Flow Direction Algorithm

The script uses a **"calculate first, fix later"** two-stage strategy to ensure full network connectivity:

**Stage 1 - Initial Calculation**:
- Use WhiteboxTools to compute D8 flow direction and flow accumulation on high-resolution DEM
- Aggregate accumulation to coarse VIC grid
- Each VIC cell flows toward its 8-neighbor with the highest accumulation greater than itself

**Stage 2 - Iterative Fix**:
- Detect cells that cannot reach the outlet
- Set disconnected cells to flow toward the connected neighbor with highest accumulation
- Repeat until all cells are connected

---

## Important: VIC Output Preprocessing (Required Step)

### Background

The Routing model expects input in the following format:
```
YEAR MONTH DAY PREC EVAP RUNOFF BASEFLOW
```
(7 columns, no header)

However, VIC 5.x output contains 22+ columns with 3 header lines. Using VIC output directly will cause:
- Extremely large discharge values (tens of thousands m³/s)
- Large negative discharge values

### Preprocessing Python Script

```python
import os
import pandas as pd

source_dir = "/path/to/vic_result"
dest_dir = "/path/to/vic_for_routing"
os.makedirs(dest_dir, exist_ok=True)

for filename in os.listdir(source_dir):
    if filename.endswith(".txt") and not filename.startswith("._"):
        source_path = os.path.join(source_dir, filename)
        new_filename = filename[:-4]
        dest_path = os.path.join(dest_dir, new_filename)

        df = pd.read_csv(source_path, sep=r'\s+', skiprows=3, header=None)
        df_out = df.iloc[:, [0, 1, 2, 3, 18, 16, 17]]
        df_out.to_csv(dest_path, sep='\t', header=False, index=False,
                     float_format='%.4f')

print(f"Processing complete, output directory: {dest_dir}")
```

---

## Pre-run Checklist

### Global Parameter File (rout_global.txt)

```
Line 3:  Flow direction file path
Line 5-6: Velocity setting (.false. + value OR .true. + file path)
Line 8-9: Diffusivity setting
Line 11-12: xmask setting
Line 14-15: fraction setting
Line 17: Station file path
Line 19: VIC input file path prefix
Line 20: Precision (usually 4)
Line 22: Output path (must end with /)
Line 24: VIC output time range
Line 25: Routing output time range
Line 27: Unit hydrograph file path
```

---

## Common Problems and Solutions

### Problem 1: Disconnected Flow Direction Network

**Symptoms**:
- Routing model runs but no output files generated
- Only a few cells are processed

**Cause**:
When aggregating high-resolution DEM flow directions to coarse VIC grid, the network may become disconnected.

**Solution**:
Use the `run_build_routing_new.py` script's "calculate first, fix later" algorithm to ensure all cells reach the outlet.

---

### Problem 2: Incorrect staloc File Format

**Symptoms**:
- No output when running routing
- Model exits immediately

**Cause**:
The staloc file must contain two lines:
```
1 XX column row -9999
NONE
```
The second line is the UH_S file path; `NONE` means recalculate.

**Solution**:
Ensure staloc file has two lines, with `NONE` or an existing .uh_s file path on the second line.

---

### Problem 3: Incorrect UH.all File Format

**Symptoms**:
- "End of file" error during runtime
- Error reading UH.all

**Cause**:
UH.all must be in 12-line format:
```
   0   0.15
   1   0.40
   2   0.25
   ...
   11  0.0
```

**Solution**:
Use the correct 12-line unit hydrograph format, each line containing index and weight value.

---

### Problem 4: Insufficient Model Dimensions

**Symptoms**:
- Error "Incorrect dimensions: Reset nrow and ncol in main to X Y"

**Cause**:
NROW and NCOL parameters in routing model source code are smaller than actual grid size.

**Solution**:
Modify `/path/to/route_1.0/src/rout.f`:
```fortran
PARAMETER (NROW = 100, NCOL = 100)  ! Adjust as needed
```
Then recompile: `make clean && make`

---

### Problem 5: Extremely Large or Negative Discharge Values

**Symptoms**:
- Monthly discharge reaches tens of thousands m³/s
- Large negative discharge values

**Cause**:
Routing model reads incorrect columns from VIC output.

**Solution**:
Must use preprocessing script to extract correct columns (see VIC Output Preprocessing above).

---

### Problem 6: Fortran Path Length Limit

**Symptoms**:
- Files exist but reported as "NOT FOUND"
- Output is all 0 or NaN

**Cause**:
Fortran string length limited to 60-80 characters, absolute paths get truncated.

**Solution**:
Create symbolic links and use relative paths:
```bash
cd /path/to/routing_config/
ln -sf /long/path/to/vic_for_routing vic_in
```

---

### Problem 7: Coordinate System Mismatch

**Symptoms**:
- Many "XX.XXXX_YYY.YYYY NOT FOUND, INSERTING ZEROS" messages
- Output discharge is all zero

**Cause**:
Grid coordinates in auxiliary files don't match VIC output filenames.

**Checking Method**:
```bash
ls vic_for_routing/ | head -5    # Check VIC file coordinates
head -6 XX_xmask.txt             # Check xmask coordinate definition
```

**Solution**:
Ensure xllcorner and yllcorner are set correctly so grid center coordinates match VIC filenames.

---

### Problem 8: Self-referencing Symlink in routing_param (Infinite Recursion)

**Symptoms**:
- `shutil.copytree` error "Too many levels of symbolic links"
- Directory structure shows `routing_param/routing_param/routing_param/...` infinite nesting
- File system operations (copy, traverse) crash or timeout

**Cause**:
A symbolic link named `routing_param` was created **inside** the `routing_param/` directory, pointing back to the `routing_param/` directory itself. This creates an infinite recursion loop. This typically happens when incorrectly handling the Fortran path length limitation.

**STRICTLY FORBIDDEN operations**:
```bash
# ❌ NEVER DO THIS! Creates a self-referencing symlink causing infinite recursion:
cd outputs/{basin_name}/routing_param/
ln -sf /path/to/outputs/{basin_name}/routing_param routing_param
# This creates routing_param/routing_param -> itself, an infinite loop!

# ❌ Also forbidden: creating any link inside routing_param that points to itself or parent routing_param
```

**Correct approach**:
```bash
# ✅ Correct: Create symlink to routing_param from OUTSIDE (e.g., /tmp)
ln -sf /long/path/to/outputs/{basin_name}/routing_param /tmp/rout_work
cd /tmp/rout_work
./rout_exe rout_global.txt

# ✅ Correct: Inside routing_param, only create symlinks to OTHER directories
cd outputs/{basin_name}/routing_param/
ln -sf /path/to/vic_for_routing vic_in          # OK: vic_in points to a different directory
ln -sf /path/to/route_1.0/src/rout rout_exe     # OK: rout_exe points to an executable
```

**KEY RULE**: Symlinks created inside `routing_param/` must NEVER be named `routing_param` and must NEVER point to a path that contains the `routing_param/` directory itself.

---

### Problem 9: UH_S File Already Exists

**Symptoms**:
- Error "Cannot open file 'XX .uh_s': File exists"

**Solution**:
```bash
rm -f "XX   .uh_s"
```

---

## Complete Workflow

```bash
# 1. Generate routing parameters
python run_build_routing_new.py

# 2. Create VIC input symlink
cd /path/to/output_dir
ln -sf /path/to/vic_for_routing vic_in

# 3. Remove old UH_S file
rm -f "XX   .uh_s"

# 4. Run routing
/path/to/route_1.0/src/rout rout_global.txt

# 5. Check results
cat rout_out/XX*.day | head -10
```

---

## Output File Description

| File | Content | Format |
|------|---------|--------|
| XX.day | Daily discharge | year month day discharge(m³/s) |
| XX.day_mm | Daily discharge | year month day discharge(mm) |
| XX.month | Monthly mean discharge | year month discharge(m³/s) |
| XX.month_mm | Monthly discharge | year month discharge(mm) |
| XX.year | Annual monthly summary | month discharge(m³/s) |
| XX.uh_s | Unit hydrograph response | Internal use |

---

## Compiling route_1.0 (If Needed)

```bash
cd /path/to/route_1.0/src
make clean
make
```

Requires gfortran compiler. After successful compilation, the `rout` executable is generated.
