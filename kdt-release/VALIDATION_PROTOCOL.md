# Model Validation Protocol -- Knowledge Dissection Toolkit

> **Version**: 1.0
> **Author**: Jianyun Zhang Research Group, Hohai University

---

## Motivation

A model is NOT validated just because it runs with developer-provided test
data. A model is validated when it produces **reasonable results using ONLY the
data prepared by your own autonomous pipeline** -- the same global/regional
datasets that every other model in your system uses.

Testing with developer data proves the binary works. Testing with your own data
proves the **knowledge infrastructure** works -- that the tools correctly
convert, transform, and prepare all inputs without silent errors.

**This distinction matters because 37% of all errors discovered during
dissection are SILENT** -- the model runs fine but produces scientifically
wrong results. These silent errors only surface when you replace developer data
with your own and compare outputs.

---

## Standard Test Basin

All models MUST be validated on a **standard test basin** as the primary test
case. Choose a basin that:

| Property | Recommendation |
|----------|---------------|
| Location | Within your forcing data coverage |
| Area | Large enough for all model types (> 1,000 km^2) |
| Climate | Representative of your study region |
| Terrain | Mixed (mountains + plains) to test diverse terrain handling |
| Period | 10+ years with good observation coverage |
| Resolution | Matches your forcing data grid |
| **Observed data** | Ground-truth discharge, soil moisture, or other key variables available |

**Exception**: If a model cannot physically apply to your standard basin (e.g.,
glacier models, permafrost models, urban drainage), use the most appropriate
alternative basin in your dataset collection.

---

## The Three-Step Validation Process

### Step 1: Developer Data Test (Prove the Binary Works)

**Goal**: Verify the model binary executes correctly using the developers' own
test data.

**Procedure**:
1. Download or locate the model's bundled example/tutorial dataset
2. Run the example exactly as documented (no modifications)
3. Verify the model completes without errors
4. Compare output with the expected results provided by developers
5. Record the run in `diagnostics/error_log.yaml`

**Success criteria**: Model runs to completion, output matches developer's
expected results within tolerance.

**What this proves**: The binary is correctly compiled and the execution
environment is valid.

**What this does NOT prove**: That your tools can prepare correct inputs.

**Done when**:
- [ ] Developer example runs successfully
- [ ] Output matches expected values
- [ ] Runtime and resource usage documented
- [ ] Any compilation/environment issues recorded as diagnostic triplets

---

### Step 2: Progressive Data Replacement (Prove the Tools Work)

**Goal**: Systematically replace developer data with your own data, one
component at a time, until the model runs entirely on pipeline-prepared inputs.

**Why progressive replacement?** If you replace everything at once and the
model fails or gives wrong results, you cannot tell which replacement caused
the problem. By replacing one component at a time and verifying after each
replacement, you isolate exactly which tool/conversion has a bug.

#### Replacement Order (easiest to hardest)

| Priority | Component | Verification |
|:--------:|-----------|-------------|
| **1** | **Meteorological forcing** | Compare key variables (T, P, SW, LW) with developer values at same location |
| **2** | **Soil/subsurface properties** | Compare soil texture, K, porosity with developer values |
| **3** | **Land cover / vegetation** | Compare dominant land use class with developer data |
| **4** | **Topography / DEM** | Compare elevation range, slope statistics |
| **5** | **River network / routing** | Compare stream order, drainage area, outlet location |
| **6** | **Initial conditions** | Run spinup, discard first 6-12 months |
| **7** | **Boundary conditions** | Compare with developer BC values |
| **8** | **Calibration parameters** | Compare with developer calibrated values (expect differences) |

#### Procedure for Each Replacement

For replacement priority `i`:

```
1. Keep all other inputs from the PREVIOUS successful run
2. Replace ONLY component i with your pipeline data (using the appropriate tool)
3. Run the model
4. Compare output with the PREVIOUS run:
   - If results are similar (within 20% for uncalibrated): Component i replacement is VALID
   - If results differ significantly: The tool for component i has a BUG
     -> Investigate the tool's unit conversions, column mappings, format
     -> Fix the tool
     -> Record the error as a diagnostic triplet
     -> Re-run and re-compare
5. Move to replacement i+1
```

**Critical rule**: Do NOT proceed to replacement `i+1` until replacement `i`
produces reasonable results. Each replacement must be validated independently.

#### Complexity-Based Strategy

**Simple models** (e.g., lumped conceptual, lake, crop):
- Few input components (forcing + parameters + geometry)
- Can often do 2-3 replacements simultaneously
- Full replacement typically achievable in one session

**Complex models** (e.g., coupled land-atmosphere, 3D groundwater, distributed
hydrology):
- Many interdependent input components
- Must follow strict one-at-a-time replacement
- May require multiple sessions
- Document intermediate states (which components are developer vs pipeline)

**Record the replacement state** in a tracking table:

```markdown
## Data Replacement Tracking -- [MODEL_NAME] on [YOUR_BASIN]

| Component | Source | Status | Notes |
|-----------|--------|--------|-------|
| Forcing | Pipeline ([YOUR_DATASET]) | Validated | T, P, SW match within 5% |
| Soil | Pipeline ([YOUR_SOIL_DB]) | Validated | K differs 2x from developer -- expected |
| Land cover | Developer data | Not yet replaced | Next priority |
| DEM | Developer data | Not yet replaced | |
| ... | | | |
```

---

### Step 3: Full Pipeline Data Run (Prove the Knowledge Infrastructure Works)

**Goal**: Run the model entirely on pipeline-prepared data for your standard
test basin and obtain physically reasonable results.

**Procedure**:
1. All inputs prepared by your pipeline tools (zero developer data remaining)
2. Run on your standard test basin for the standard period
3. Compare results with:
   - Published literature values for the basin
   - Other validated models' results for the same basin
   - Physical reasonableness checks (water balance, seasonal cycle, magnitude)

**Success criteria**:

| Model type | Minimum validation |
|-----------|-------------------|
| **Hydrological** (discharge) | Mean Q within 50% of observed/literature, correct seasonal cycle, r > 0.5 |
| **Crop** (yield) | Within 30% of census/literature yield, correct growing season |
| **Water quality** | Correct order of magnitude for key variables |
| **Lake/reservoir** | Correct seasonal temperature cycle, realistic stratification |
| **Flood** | Non-zero flood depth in floodplain areas, depth < 20m |
| **Groundwater** | Water table in expected range, correct flow direction |
| **Routing** | Discharge at outlet, r > 0.5 vs existing routing |

**What "reasonable" means**: Uncalibrated results will NOT match observations
perfectly. But they must be:
- Same order of magnitude as published values
- Correct seasonal/temporal pattern (e.g., monsoon peak in summer, not winter)
- Physically possible (no negative discharge, no 1000 degC temperatures)
- Not dominated by artifacts (spinup, unit errors, missing data)

**Done when**:
- [ ] All inputs from pipeline data (zero developer data)
- [ ] Model runs to completion on standard test basin
- [ ] Results pass physical reasonableness checks
- [ ] Comparison with other models documented
- [ ] All errors found during validation recorded as diagnostic triplets
- [ ] SKILL.md updated with "Validated Results" section

---

## Validation Checklist (Must Complete for Every Model)

```
[ ] Step 1: Developer data test passed
[ ] Step 2a: Forcing replaced with [YOUR_FORCING] -- results reasonable
[ ] Step 2b: Soil replaced with [YOUR_SOIL_DB] -- results reasonable
[ ] Step 2c: Land cover replaced with [YOUR_LANDCOVER] -- results reasonable
[ ] Step 2d: DEM replaced with [YOUR_DEM] -- results reasonable
[ ] Step 2e: All remaining components replaced -- results reasonable
[ ] Step 3: Full pipeline data run -- results reasonable
[ ] All errors recorded in error_log.yaml
[ ] All significant errors promoted to triplets.yaml
[ ] SKILL.md updated with validated results
[ ] Data replacement tracking table completed
```

---

## Anti-Patterns (What NOT to Do)

1. **"It works with test data, ship it"** -- Developer data proves the binary
   works, NOT the knowledge infrastructure. You must complete all 3 steps.

2. **"I replaced everything at once and it works"** -- You got lucky. If it had
   failed, you'd have no idea which component caused the failure. Always
   replace one at a time.

3. **"The results are different but the model runs"** -- Different HOW? 10%
   different is calibration. 10x different is a unit error. 1000x different is
   a column mapping bug. Always quantify and explain the difference.

4. **"I'll calibrate it later"** -- Calibration fixes PARAMETERS, not DATA
   PREPARATION bugs. If forcing has wrong units, calibration will compensate by
   producing wrong parameters. The model will "work" on the calibration period
   but fail on any new period. Fix the data first, calibrate later.

5. **"The model doesn't have a [YOUR_BASIN] example"** -- Then BUILD one.
   That is the entire point of the knowledge infrastructure -- to enable
   running any model on any basin autonomously.

6. **"The binary won't build, I'll write a Python surrogate"** -- NO. A Python
   reimplementation of the model equations proves the MATH works, not that your
   pipeline can drive the REAL MODEL. The whole point of KDT is to run the
   actual model software (compiled binary, native package) in its intended mode
   (distributed/gridded, not lumped) with pipeline-prepared data. Analytic
   surrogates are ONLY acceptable when:
   - The source code is genuinely unavailable (proprietary, dead link), AND
   - The user has explicitly approved the fallback.

7. **"I'll run it lumped to save time"** -- Models designed for
   distributed/gridded application MUST be run distributed. Gridded forcing
   data exists. Running a gridded model as a lumped basin-average wastes the
   spatial information and produces worse results. Run it the way it was
   designed.

---

## Validation Status Labels

Use these labels in SKILL.md and knowledge_infrastructure.yaml:

| Label | Meaning |
|-------|---------|
| `binary_only` | Step 1 passed -- model runs with developer data |
| `partial_replacement` | Step 2 in progress -- some components replaced |
| `full_replacement` | Step 2 complete -- all components replaced individually |
| `production_validated` | Step 3 passed -- full pipeline data, reasonable results |

---

## Calibration/Validation Period Split (Mandatory)

**All calibrated models MUST use a proper temporal split.** Define standard
periods for your test basin:

| Period | Purpose |
|--------|---------|
| **Spinup** | Initialize model states; discard from ALL metrics |
| **Calibration** | Optimize parameters ONLY on this period |
| **Validation** | Evaluate generalization; NEVER use in the objective function |

For example, with 11 years of data (e.g., 1980-1990):

| Period | Years | Purpose |
|--------|-------|---------|
| Spinup | Year 1 | Initialize model states; discard |
| Calibration | Years 2-6 | Optimize parameters |
| Validation | Years 7-11 | Evaluate generalization |

**Rules:**
1. The optimization/objective function MUST only see calibration period data.
2. Validation metrics MUST be computed on the held-out period SEPARATELY.
3. Both calibration AND validation metrics must be recorded in `stage_log.json`.
4. Full-period metrics may be reported additionally, but NEVER as the sole
   metric.

### Helper tools

Use the standard helpers in `validators/standard_calval.py`:

```python
from validators.standard_calval import (
    split_data,              # Split dates/obs/sim into cal and val subsets
    compute_calval_metrics,  # Compute NSE/KGE/PBIAS/r for both periods
    calval_objective,        # Wrapper for scipy.optimize that ONLY uses cal data
)

# In your validation script:
metrics = compute_calval_metrics(dates, obs_Q, sim_Q)
# Returns: {'calibration': {NSE, KGE, PBIAS, r, n},
#           'validation':  {NSE, KGE, PBIAS, r, n},
#           'full':        {NSE, KGE, PBIAS, r, n}}
```

### Preflight checker

Run the cal/val split checker before submitting validation results:

```bash
python validators/check_calval_split.py [MODEL_NAME]
python validators/check_calval_split.py --all
python validators/check_calval_split.py --all --json
```

Statuses: **PASS** (proper split), **WARN** (ambiguous), **FAIL** (data
leakage), **SKIP** (not applicable).

### Recording cal/val in stage_log.json

The `s8_validation` entry MUST include these fields for calibrated models:

```json
{
  "s8_validation": {
    "period_calibration": "[CAL_START]-[CAL_END]",
    "period_validation": "[VAL_START]-[VAL_END]",
    "metrics": {
      "NSE_cal": 0.85,
      "KGE_cal": 0.87,
      "NSE_val": 0.72,
      "KGE_val": 0.75,
      "PBIAS_val": 12.3,
      "NSE": 0.79,
      "KGE": 0.82
    }
  }
}
```

---

## Integration with Knowledge Dissection Phases

This validation protocol extends Phase 6 (Package Assembly) of the dissection
process:

| Dissection Phase | Validation Step |
|-----------------|-----------------|
| Phase 6.1: Package assembly | Step 1 (developer data test) |
| Phase 6.2: Agent read-through | N/A |
| **Phase 6.3: End-to-end verification** | **Steps 2 + 3 (progressive replacement + full autonomous run)** |

Phase 6.3 is NOT complete until Step 3 passes. A model with only Step 1
completed has status **"binary validated, knowledge infrastructure
unvalidated"**.

---

*Part of the Knowledge Dissection Toolkit by the Jianyun Zhang Research Group,
Hohai University.*
