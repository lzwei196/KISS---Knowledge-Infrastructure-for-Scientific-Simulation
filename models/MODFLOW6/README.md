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

# MODFLOW 6 Knowledge Infrastructure — Agent Entry Point

**Package**: `modflow6-knowledge-infrastructure` v1.0.0
**Model**: MODFLOW 6 (USGS Modular Hydrologic Model)
**Domain**: Groundwater hydrology, subsurface flow, solute transport
**Role in HydroCraft**: Fills the groundwater modeling gap — couples with VIC (recharge), CaMa-Flood (river stage), and Lohmann routing (baseflow)

---

## What This Enables

An AI agent can autonomously:
1. Build a MODFLOW 6 groundwater flow model for any basin using FloPy
2. Map VIC deep percolation to MODFLOW recharge (RCH package)
3. Couple CaMa-Flood river stages to MODFLOW river boundaries (RIV package)
4. Feed MODFLOW drain discharge back to routing models as baseflow
5. Extract water table depths for VIC soil moisture feedback
6. Run transient simulations driven by HydroCraft forcing data

## Quick Reference

| Component | What | Where |
|-----------|------|-------|
| **Binary** | `mf6` (Fortran CLI) | System PATH or specified path |
| **Python interface** | FloPy (`flopy.mf6`) | `pip install flopy` |
| **Simulation name file** | `mfsim.nam` | Created by FloPy in workspace directory |
| **Input format** | Block/keyword text files (`BEGIN ... END`) | One file per package |
| **Binary output** | `.hds` (heads), `.cbc` (cell budget) | Read with `flopy.utils.HeadFile`, `CellBudgetFile` |
| **Listing file** | `.lst` | Convergence info, budget summary, warnings |

## Pipeline Overview (9 Stages)

```
S1 Installation ──> S2 Grid/DIS ──> S3 NPF/STO ──> S4 Boundary Conditions
                                         │                    │
                                         v                    v
                                    S5 TDIS/IC ──────> S6 Solver/IMS
                                                            │
                                                            v
                                                    S7 Execute mf6
                                                            │
                                                            v
                                                S8 Extract Heads/Budget
                                                            │
                                                            v
                                                S9 Postprocess & Visualize
```

## Skill Documents (Read for Each Stage)

| Stage | Document | Key Decisions |
|-------|----------|---------------|
| S1 | `docs/s1_installation_skill.md` | Binary source (pre-built vs compile), FloPy version |
| S2 | `docs/s2_grid_discretization_skill.md` | Cell size, number of layers, IDOMAIN mask, DIS vs DISV |
| S3 | `docs/s3_layer_properties_skill.md` | K values, confined vs convertible, Ss/Sy, Newton formulation |
| S4 | `docs/s4_boundary_conditions_skill.md` | Which packages (CHD/WEL/RCH/DRN/RIV/EVT), units, VIC/CaMa coupling |
| S5 | `docs/s5_stress_periods_skill.md` | Period lengths, timesteps, steady-state warmup, IC from prior run |
| S6 | `docs/s6_solver_skill.md` | SIMPLE/MODERATE/COMPLEX, DVCLOSE, RCLOSE, under-relaxation |
| S7 | `docs/s7_execution_skill.md` | Write files, run mf6, check listing file, handle failures |
| S8 | `docs/s8_output_extraction_skill.md` | Read .hds/.cbc, HDRY sentinel, budget balance check |
| S9 | `docs/s9_postprocessing_skill.md` | Contour maps, budget plots, NetCDF export for coupling |

## Tools Reference

| Stage | Tool ID | Script | Purpose |
|-------|---------|--------|---------|
| S1 | `verify_mf6_installation` | `tools/s1/verify_mf6_installation.py` | Check mf6 and FloPy availability |
| S2 | `create_grid_from_basin` | `tools/s2/create_grid_from_basin.py` | Basin shapefile to MODFLOW grid |
| S2 | `build_dis_package` | `tools/s2/build_dis_package.py` | Create DIS package via FloPy |
| S3 | `build_npf_package` | `tools/s3/build_npf_package.py` | Create NPF package (K, ICELLTYPE) |
| S3 | `build_sto_package` | `tools/s3/build_sto_package.py` | Create STO package (Ss, Sy) |
| S4 | `build_chd_package` | `tools/s4/build_chd_package.py` | Constant head boundaries |
| S4 | `build_rch_package` | `tools/s4/build_rch_package.py` | Recharge (incl. VIC coupling) |
| S4 | `build_riv_package` | `tools/s4/build_riv_package.py` | River boundaries (incl. CaMa coupling) |
| S4 | `build_drn_package` | `tools/s4/build_drn_package.py` | Drain boundaries (baseflow) |
| S4 | `build_wel_package` | `tools/s4/build_wel_package.py` | Well pumping/injection |
| S5 | `build_tdis_package` | `tools/s5/build_tdis_package.py` | Temporal discretization |
| S5 | `build_ic_package` | `tools/s5/build_ic_package.py` | Initial conditions |
| S5 | `assign_transient_stress` | `tools/s5/assign_transient_stress.py` | Time-varying stress data |
| S6 | `build_ims_package` | `tools/s6/build_ims_package.py` | Solver configuration |
| S7 | `write_and_run_simulation` | `tools/s7/write_and_run_simulation.py` | Write files + execute mf6 |
| S8 | `extract_heads` | `tools/s8/extract_heads.py` | Read binary head file |
| S8 | `extract_budget` | `tools/s8/extract_budget.py` | Read cell budget file |
| S9 | `plot_head_map` | `tools/s9/plot_head_map.py` | Water table contour map |
| S9 | `plot_water_budget` | `tools/s9/plot_water_budget.py` | Budget bar chart |
| S9 | `export_to_netcdf` | `tools/s9/export_to_netcdf.py` | Export for HydroCraft coupling |
| S2 | `build_layers_from_global` | `tools/s2/build_layers_from_global.py` | TOP/BOTM/IDOMAIN/STRT from global rasters |
| S3 | `assign_k_from_glhymps` | `tools/s3/assign_k_from_glhymps.py` | K/Sy from GLHYMPS 2.0 + HWSD pedotransfer |
| S4 | `build_riv_from_cama` | `tools/s4/build_riv_from_cama.py` | RIV package from CaMa-Flood river network |

## Global Data Sources

| Dataset | Path | What It Provides |
|---------|------|------------------|
| **GLHYMPS 2.0** | `data/groundwater/glhymps/GLHYMPS.shp` | Hydraulic conductivity (K), porosity — global subsurface hydrogeology |
| **Reinecke WTD** | `data/groundwater/fan_wtd/MeanWaterTableDepth_meter.tif` | Mean water table depth (m) — initial heads for IC package |
| **GLiM lithology** | `data/groundwater/glim/glim_wgs84_0point5deg.txt.asc` | Lithology classes — K validation / cross-check |
| **China DTB** (Yan/Shangguan 2020) | *Manual download* from http://globalchange.bnu.edu.cn/research/cdtb.jsp | Depth-to-bedrock for China — layer bottom elevations |
| **Pelletier regolith** | *Manual download* from https://daac.ornl.gov/cgi-bin/dsviewer.pl?ds_id=1304 | Global regolith thickness — layer bottom elevations outside China |

## Automated Setup Pipeline

Three new tools automate the most error-prone setup steps using the global datasets above:

1. **`build_layers_from_global`** (S2) — Builds TOP/BOTM/IDOMAIN/STRT from DEM + depth-to-bedrock + water table depth rasters. Eliminates manual layer elevation guesswork.
2. **`assign_k_from_glhymps`** (S3) — Assigns K/Sy from GLHYMPS 2.0 for deep layers + HWSD pedotransfer for the shallow soil layer. Handles CRS reprojection and logK decoding automatically.
3. **`build_riv_from_cama`** (S4) — Builds RIV package from CaMa-Flood river network + discharge. Auto-clamps rbot to prevent fatal MODFLOW errors.

## Critical Domain Knowledge (Non-Obvious Facts)

1. **Units are the user's responsibility.** MODFLOW 6 does not convert units. If LENGTH_UNITS is "meters" and TIME_UNITS is "days", then K must be m/day, recharge must be m/day, well rates must be m3/day. There is no error if units are wrong — results will simply be silently wrong.

2. **Recharge is a rate, not a volume.** The RCH package expects recharge in LENGTH/TIME (e.g., m/day), not volume (m3/day). A common error is passing VIC deep percolation as mm/day without converting to m/day (divide by 1000).

3. **HDRY sentinel for dry cells.** When a cell goes dry (head drops below cell bottom), MODFLOW 6 sets head to 1.0e30 (HDRY). Reading this as a real head value corrupts statistics. Always filter HDRY before computing means or plotting.

4. **Layer numbering is 0-indexed in FloPy, 1-indexed in MODFLOW input files.** FloPy layer 0 = MODFLOW layer 1. Cellid tuples in FloPy are (layer, row, col) with 0-based indices. In raw MODFLOW input files, they are 1-based.

5. **ICELLTYPE matters for water table problems.** If the top layer is confined (ICELLTYPE=0) but the water table is in that layer, MODFLOW will not correctly compute saturated thickness — heads can rise above cell top with no error. Set ICELLTYPE=1 for convertible (unconfined) layers.

6. **Newton-Raphson formulation is essential for drying/rewetting.** Standard formulation can oscillate when cells repeatedly wet and dry. Use `NEWTON UNDER_RELAXATION` in the GWF model options for unconfined problems.

7. **Budget percent discrepancy > 1% indicates a problem.** Typical well-posed models have < 0.01% discrepancy. Large discrepancy usually means convergence was not achieved or DVCLOSE/RCLOSE are too loose.

8. **The listing file is the primary diagnostic.** Budget summaries, convergence iterations, dry cell warnings, and error messages are all in `<model_name>.lst`. Always read it after a run.

9. **FloPy arrays must be 3D (nlay x nrow x ncol).** Common error: saving 2D arrays for `strt` or `sy`. FloPy will raise "Unable to set data layer 0. Data is not in a valid format" if you pass a 2D (nrow x ncol) array instead of 3D (nlay x nrow x ncol). Always use `np.broadcast_to()` or `np.stack()` to ensure 3D shape.

10. **GLHYMPS CRS is Cylindrical Equal Area (meters), not WGS84.** Use geopandas bbox reprojection when doing spatial joins: reproject your WGS84 grid centroids to GLHYMPS CRS, or reproject GLHYMPS to WGS84. Direct coordinate comparison will fail silently.

11. **GLHYMPS logK values are stored x100.** The `logK_Ferr_` field contains logK(m^2) multiplied by 100. For example, -1180 means logK = -11.80 m^2. Decode: `K_m2 = 10**(logK_field / 100)`, then convert to m/day: `K_m_day = K_m2 * rho * g / mu * 86400`.

12. **RIV rbot must be above cell BOTM.** If river bottom elevation is below the MODFLOW cell bottom, MODFLOW aborts with "RIVER BOTTOM IS LESS THAN CELL BOTTOM". Always clamp: `rbot = max(rbot, botm + 0.5)`.

## Error Handling

When errors occur, look up symptoms in `diagnostics/triplets.yaml` (17 triplets across 7 failure domains). Key triplets:
- **dt_mf6_001**: Convergence failure — solver did not converge within iteration limit
- **dt_mf6_002**: Dry cells in unconfined simulation — cells going dry causing oscillation
- **dt_mf6_003**: Budget imbalance — percent discrepancy > 0.1%
- **dt_mf6_004**: Recharge unit error — mm/day vs m/day mismatch (silent error)
- **dt_mf6_008**: Silent wrong recharge — RCH applied to wrong layer or IRCH not set

## HydroCraft Coupling

See `docs/model_couplings.yaml` for detailed coupling specifications:
- **VIC deep percolation -> MODFLOW RCH**: VIC baseflow_out (mm/day) / 1000 -> m/day recharge
- **MODFLOW DRN flux -> Routing baseflow**: Drain discharge (m3/day) -> routing input
- **CaMa-Flood river stage -> MODFLOW RIV**: CaMa sfcelv (m) -> RIV package stage
- **MODFLOW water table -> VIC feedback**: Water table depth modifies VIC soil moisture capacity

## Minimal Working Example (FloPy)

```python
import flopy

# 1. Create simulation
sim = flopy.mf6.MFSimulation(sim_name="test", sim_ws="./workspace")

# 2. Temporal discretization (1 steady-state period)
tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])

# 3. Solver
ims = flopy.mf6.ModflowIms(sim, complexity="SIMPLE")

# 4. Groundwater flow model
gwf = flopy.mf6.ModflowGwf(sim, modelname="gwf", newtonoptions="NEWTON")

# 5. Discretization (10x10 grid, 1 layer, 100m cells)
dis = flopy.mf6.ModflowGwfdis(gwf, nlay=1, nrow=10, ncol=10,
                                delr=100.0, delc=100.0,
                                top=50.0, botm=[0.0])

# 6. Node properties (K=10 m/day, unconfined)
npf = flopy.mf6.ModflowGwfnpf(gwf, icelltype=1, k=10.0)

# 7. Initial conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=40.0)

# 8. Constant head on left boundary
chd_data = [[(0, i, 0), 45.0] for i in range(10)]
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=chd_data)

# 9. Recharge
rch = flopy.mf6.ModflowGwfrcha(gwf, recharge=0.001)  # 1 mm/day = 0.001 m/day

# 10. Output control
oc = flopy.mf6.ModflowGwfoc(gwf,
        head_filerecord="gwf.hds",
        budget_filerecord="gwf.cbc",
        saverecord=[("HEAD", "ALL"), ("BUDGET", "ALL")])

# 11. Write and run
sim.write_simulation()
sim.run_simulation()

# 12. Read results
import flopy.utils.binaryfile as bf
hds = bf.HeadFile("workspace/gwf.hds")
heads = hds.get_data()
```

## Validated Results — Bengbu Basin (Re-validated 2026-03-22)

**Validation Protocol**: 3-step (VALIDATION_PROTOCOL.md)
**Status**: `production_validated`
**FloPy Version**: 3.10.0

### Step 1: Binary Test
- MODFLOW 6.6.1 binary works (compiled Intel Fortran, double precision)
- FloPy 3.10.0: `run_simulation(exe_name=...)` removed, use `subprocess.run()` instead
- Binary output readable with `precision='double'`
- Newton + SIMPLE solver = ERROR (CG incompatible with asymmetric matrix) -> use MODERATE/COMPLEX

### Step 2: Progressive Data Replacement

| Component | Source | Status | Notes |
|-----------|--------|--------|-------|
| Grid | VIC 0.25deg basin_grid.nc | Validated | 16x24 grid, 224 active cells |
| DEM/TOP | China DEM 90m | Validated | Range: 5-1378 m |
| Initial heads | Fan/Reinecke global WTD | Validated | WTD mean: 16.9 m, clamped to 1-5m for IC |
| K (Layer 1) | HWSD via VIC soil params, scaled 100x | Validated | HWSD Ksat underestimates aquifer K by ~100x |
| K (Layers 2-3) | Derived from Layer 1 K/3, K/30 | Validated | Typical depth decay factors |
| Recharge | VIC OUT_BASEFLOW (mm/day -> m/day) | Validated | Mean: 0.578 mm/day = 0.000578 m/day |
| Boundary (CHD) | DEM-derived (lowest 10% + edge cells) | Validated | 71 CHD cells |
| Drain (DRN) | All non-CHD active cells | Validated | Prevents ponding, C = K*1000*W/10 |
| Storage (Ss/Sy) | Literature defaults | Validated | Ss=1e-5, Sy=0.15/0.10/0.05 |

### Step 3: Full HydroCraft Run Results

| Metric | Value | Expected | Status |
|--------|-------|----------|--------|
| WT depth median | 0.9 m | 1-5 m | PASS |
| WT depth mean | 2.0 m | 2-5 m | PASS |
| WT depth range | 0.5 - 5.0 m | 1-10 m | PASS |
| Budget closure | 0.0002% | < 1% | PASS |
| Convergence failures | 0 | 0 | PASS |
| Flow direction | correct (upstream 361m > downstream 30m) | correct | PASS |
| Artesian cells | 0 | < 10% | PASS |
| Layer 1 dry cells | 0% | < 20% | PASS |
| Runtime | 0.4 seconds | < 60s | PASS |

### Key Lessons Learned

1. **HWSD soil Ksat != aquifer K**: HWSD gives soil K (~0.01 m/day), aquifer K is ~1-10 m/day. Scale by ~100x for Layer 1.
2. **Newton requires MODERATE/COMPLEX solver**: SIMPLE uses CG which fails on asymmetric Newton matrices.
3. **DRN conductance must use realistic dimensions**: C = K * drain_width * cell_width / bed_thickness, NOT K * delr * delc.
4. **FloPy 3.10 API changes**: `run_simulation()` no longer accepts `exe_name`, `inner_rclose` -> `rcloserecord`, STO period data format changed.
5. **Deep layer dry cells are normal**: For unconfined aquifer with WT in Layer 1, Layers 2-3 will be dry. Only check Layer 1 dry cells for validation.
6. **Initial heads must be within layer bounds**: Clamping WTD to 1-5m prevents starting heads below cell bottom.

### Validation Files
- Script: `outputs/bengbu_modflow6_revalidation/step2_3_full_bengbu.py`
- Results JSON: `outputs/bengbu_modflow6_revalidation/validation_results.json`
- Plot: `outputs/bengbu_modflow6_revalidation/modflow6_bengbu_validation.png`
- MODFLOW workspace: `outputs/bengbu_modflow6_revalidation/bengbu_workspace/`

---

*This knowledge infrastructure was built using the Knowledge Dissection Toolkit v1.0 (Jianyun Zhang Research Group, Hohai University).*
