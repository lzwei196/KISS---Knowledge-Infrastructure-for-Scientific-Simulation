# CLAUDE.md Template — KI-Powered Hydrological Simulation

> **This is a template.** Copy it to your project root as `CLAUDE.md` and fill in the paths
> marked with `<YOUR_...>`. Then symlink for other providers:
> ```bash
> ln -sf CLAUDE.md AGENTS.md   # Codex
> ln -sf CLAUDE.md QWEN.md     # Qwen
> ```

---

## About

This project uses Knowledge Infrastructure (KI) to enable AI agents to autonomously
run process-based hydrological models. The agent reads this file for project context,
then reads each model's `SKILL.md` for operational details.

### Supported Models

| Domain | Model | Binary | KI Path |
|--------|-------|--------|---------|
| Hydrology | VIC 5.1.0 | `<YOUR_PROJECT>/model/VIC-5.1.0/vic/drivers/classic/vic_classic.exe` | `models/VIC/knowledge_infrastructure/` |
| River Routing | Lohmann | `<YOUR_PROJECT>/model/route_1.0/src/rout` | `models/Lohmann_Routing/knowledge_infrastructure/` |
| Flood Routing | CaMa-Flood 4.20 | `<YOUR_PROJECT>/model/cmf_v420_pkg/src/MAIN_cmf` | `models/CaMa_Flood/knowledge_infrastructure/` |

---

## Environment Setup

```bash
# Activate Python environment before running ANY script
source <YOUR_PROJECT>/python_env/bin/activate

# If activate fails, use the binary directly:
<YOUR_PROJECT>/python_env/bin/python <script.py>
```

---

## Data Registry

**Fill in your local data paths. The agent must NOT guess paths.**

| Dataset | Path | Coverage | Resolution |
|---------|------|----------|------------|
| Meteorological forcing | `<YOUR_FORCING_DIR>/` | Your region | 3-hourly or daily |
| Soil (HWSD) | `<YOUR_SOIL_DIR>/HWSD_RASTER/hwsd.bil` | Global | 30 arcsec |
| Soil properties DB | `<YOUR_SOIL_DIR>/HWSD.mdb` | Global | 47,732 units |
| Land cover (AVHRR) | `<YOUR_LANDCOVER_DIR>/AVHRR_1km_LANDCOVER.tif` | Global | 1 km |
| DEM | `<YOUR_DEM_DIR>/dem.tif` | Your region | 90m or 30m |
| Observed discharge | `<YOUR_OBS_DIR>/` | Your stations | Daily |

### Data Sources for Global Coverage

If you need global datasets, these are freely available:

| Dataset | Source | Use |
|---------|--------|-----|
| HWSD v1.2 soil | [FAO](https://www.fao.org/soils-portal/data-hub/) | Soil parameters |
| AVHRR land cover | [USGS](https://www.usgs.gov/centers/eros) | Vegetation classification |
| SRTM 30m DEM | [NASA EarthData](https://earthdata.nasa.gov/) | Basin delineation, routing |
| Copernicus GLO-30 | [AWS Open Data](https://registry.opendata.aws/copernicus-dem/) | Alternative DEM |
| NASA POWER | [power.larc.nasa.gov](https://power.larc.nasa.gov/) | Meteorological forcing (API) |
| GRDC discharge | [grdc.bafg.de](https://grdc.bafg.de/) | Observed streamflow |

---

## Knowledge Infrastructure

Every model has a KI directory with validated tools and documentation:

```
models/<ModelName>/knowledge_infrastructure/
├── SKILL.md              # Operational manual — READ BEFORE RUNNING
├── tools/                # Validated data preparation scripts — USE THESE
├── diagnostics/
│   └── triplets.yaml     # Known errors: symptom → diagnosis → remedy
└── preflight_check.py    # Run before model execution
```

**Rule: ALWAYS read a model's SKILL.md before running it. NEVER write custom scripts
when a validated tool exists in tools/.**

---

## Model Selection Guide

| User wants... | Use this workflow |
|--------------|-------------------|
| River discharge / streamflow | VIC → Lohmann Routing |
| Flood inundation / flood map | VIC → CaMa-Flood |
| Both discharge and flood depth | VIC → CaMa-Flood (outputs both) |

---

## Workflow: VIC + Lohmann Routing (Discharge Only)

### Step 0: Basin Delineation (if no shapefile provided)

```bash
python <YOUR_DELINEATION_TOOL> \
  --lat <latitude> --lng <longitude> \
  --output data/shp/<basin_name>_shp \
  --name <basin_name>_boundary
```

### Step 1: Configure Paths

Edit `models/VIC/knowledge_infrastructure/config_paths.py`:
- Set `BASIN_NAME`, `YEAR_START`, `YEAR_END`
- Set `RESOLUTION` (0.25 or 0.1)
- Set shapefile path

### Step 2: Generate Grid

```bash
python models/VIC/knowledge_infrastructure/s1_grid/make_basin_grid_nc.py
```
Output: `outputs/<basin>/vic_temp/grid/basin_grid.nc`

### Step 3: Soil Parameters

```bash
python models/VIC/knowledge_infrastructure/s3_soil/fill_parameters1.py
python models/VIC/knowledge_infrastructure/s3_soil/fill_parameters2.py
```
Output: `outputs/<basin>/vic_temp/soil/SOIL_PARAM_COMPLETE.txt`

### Step 4: Vegetation Parameters

```bash
python models/VIC/knowledge_infrastructure/s4_veg/process_vegetation_detailed.py
```
Output: `outputs/<basin>/vic_temp/veg/VEG_PARAM.txt`

### Step 5: Meteorological Forcing

```bash
python models/VIC/knowledge_infrastructure/s2_forcing/forcing_1d.py
python models/VIC/knowledge_infrastructure/s2_forcing/process_forcing.py
```
**This step takes 5-30 minutes. Run in background and poll for completion.**

Output: `outputs/<basin>/vic_temp/forcing/forcing_final/`

### Step 6: VIC Global Parameter File

Create or verify the global parameter file referencing all inputs.

### Step 7: Run VIC

```bash
<YOUR_PROJECT>/model/VIC-5.1.0/vic/drivers/classic/vic_classic.exe \
  -g outputs/<basin>/vic_temp/global_param.txt
```
**Takes 1-20 minutes depending on basin size and period.**

Output: `outputs/<basin>/vic_result/`

### Step 8: Preprocess VIC Output (CRITICAL)

```bash
python models/Lohmann_Routing/knowledge_infrastructure/preprocess_vic_for_routing.py
```
**This converts VIC 22-column output to 7-column routing input. Without this step,
routing reads wrong columns and produces garbage.**

### Step 9: Build Routing Parameters + Run

```bash
python models/Lohmann_Routing/knowledge_infrastructure/s5_routing_param/run_build_routing_new.py

# Delete old UH files before re-running
rm -f *.uh_s

# Run routing
<YOUR_PROJECT>/model/route_1.0/src/rout rout_global.txt
```

### Step 10: Visualize Results

Generate discharge comparison plot with observed data (if available).

---

## Workflow: VIC + CaMa-Flood (Discharge + Flood Inundation)

**Follow VIC Steps 0-7 above, then:**

**DO NOT follow Steps 8-10 (those are Lohmann routing only).**

### CaMa Step 1: Convert VIC Output to NetCDF

```bash
python models/CaMa_Flood/knowledge_infrastructure/vic_post/process_vic_for_cama.py \
  --input outputs/<basin>/vic_result \
  --output outputs/<basin>/cama_input \
  --start <start_year> --end <end_year>
```

### CaMa Step 2: Setup CaMa Basin (Automated)

```bash
python <YOUR_CAMA_SETUP_SCRIPT> \
  --basin_name <basin> \
  --grid_nc outputs/<basin>/vic_temp/grid/basin_grid.nc \
  --start_year <start> --end_year <end>
```

This handles: map regionalization, input matrix, channel parameters, run script.

### CaMa Step 3: Run CaMa-Flood

```bash
bash <YOUR_PROJECT>/model/cmf_v420_pkg/gosh/run_<basin>_1d_nc.sh
```

Output: NetCDF files with `outflw` (m³/s), `rivdph` (m), `flddph` (m), `fldfrc` (0-1).

---

## Critical Rules

### Unit Traps (Silent Errors — Model Runs Fine, Results Are Wrong)

| Model | Trap | Impact if wrong |
|-------|------|-----------------|
| VIC | Forcing column order must match global_param | Wrong variables mapped |
| VIC | Precipitation unit depends on source (CMFD: mm/3hr, MSWX: mm/3hr, NASA POWER: mm/day÷24) | Orders of magnitude error |
| Lohmann | Fortran path limit ~72 chars | Crash or silent truncation |
| CaMa-Flood | Must use ABSOLUTE paths in namelist | STOP 10 error |
| CaMa-Flood | Maps must be regenerated per basin | Wrong river network |
| CaMa-Flood | Input matrix must match VIC grid, not CaMa domain | Near-zero flux |

### Agent Discipline

1. **PLAN FIRST**: Before executing anything, show a numbered plan with data paths and
   estimated times. Wait for user confirmation.
2. **VERIFY EACH STEP**: After each step, check output exists and values are reasonable.
   Report result before moving on.
3. **READ SKILL.md**: Read `models/<Model>/knowledge_infrastructure/SKILL.md` BEFORE
   running any model.
4. **USE VALIDATED TOOLS**: Never write custom scripts when a KI tool exists.
   Custom scripts reintroduce bugs the tools were built to prevent.
5. **CHECK UNITS**: For EVERY model, check the unit conversion table in its SKILL.md
   BEFORE preparing inputs. The model will NOT warn you if units are wrong.

### Timing Rules

| Step | Typical Runtime | Notes |
|------|----------------|-------|
| Basin delineation | 30s - 3 min | DEM processing |
| Grid generation | 5 - 15s | Fast |
| Soil/vegetation | 30s - 2 min each | Can run in parallel |
| Forcing extraction | 5 - 30 min | Long-running, use background |
| VIC model | 1 - 20 min | Depends on grid cells × years |
| Lohmann routing | 10s - 5 min | Fast |
| CaMa-Flood | 1 - 10 min | Hydrodynamic routing |

**Do NOT kill or restart processes that appear silent.** Many steps produce output in
bursts, not continuously. A process printing nothing for 1-2 minutes is NORMAL.

---

## Adapting This Template

1. Replace all `<YOUR_...>` placeholders with your actual paths
2. Add your data sources to the Data Registry table
3. Add any additional models you've dissected
4. Copy model KI directories from the KDT output into `models/<Name>/knowledge_infrastructure/`
5. Symlink for other providers: `ln -sf CLAUDE.md AGENTS.md` etc.
6. Test with each provider using the test prompts in `AGENT_SERVICE_GUIDE.md`

---

*Template from the Knowledge Dissection Toolkit v4.0*
*See AGENT_SERVICE_GUIDE.md for full deployment documentation*
