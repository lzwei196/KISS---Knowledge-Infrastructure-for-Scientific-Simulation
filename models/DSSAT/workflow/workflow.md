# DSSAT-CSM Pipeline Workflow

> Visual and textual reference for the 9-stage DSSAT simulation pipeline.
> Generated from `knowledge_infrastructure.yaml` for DSSAT-CSM v4.8.5 (Build 41).

---

## Pipeline Overview

```
                        ┌─────────────────┐
                        │      START      │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
              ▼                  ▼                   ▼
   ┌──────────────────┐ ┌───────────────┐ ┌──────────────────┐
   │ S1. Experiment   │ │ S2. Weather   │ │ S3. Soil         │
   │     Design       │ │     Prep      │ │     Setup        │
   │  [evaluative]    │ │ [procedural]  │ │  [procedural]    │
   └──┬───────────┬───┘ └───────┬───────┘ └───┬──────────────┘
      │           │             │              │
      │     ┌─────┘             │              │
      │     │                   │              ▼
      │     │    ┌──────────────────────┐  ┌──────────────────┐
      │     │    │ S4. Genotype         │  │ S6. Initial      │
      │     │    │     Configuration    │  │     Conditions   │
      │     │    │  [evaluative]        │  │  [evaluative]    │
      │     │    └──────────┬───────────┘  └──────┬───────────┘
      │     │               │                     │
      ▼     ▼               │                     │
   ┌──────────────────┐     │                     │
   │ S5. Simulation   │     │                     │
   │     Controls     │     │                     │
   │  [evaluative]    │     │                     │
   └──────┬───────────┘     │                     │
          │                 │                     │
          ▼                 ▼                     ▼
   ┌──────────────────┐     │                     │
   │ S7. Management   │     │                     │
   │     Specification│     │                     │
   │  [evaluative]    │     │                     │
   └──────┬───────────┘     │                     │
          │                 │                     │
          └────────┬────────┴─────────────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │ S8. Batch        │
        │     Execution    │
        │  [debugging]     │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ S9. Output       │
        │     Parsing      │
        │  [procedural]    │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │     FINISH       │
        └──────────────────┘
```

**Knowledge type legend:**
- **[procedural]** — deterministic computations; encoded as validated tools
- **[evaluative]** — decisions requiring domain judgement; encoded as skill documents
- **[debugging]** — execution with legacy code; encoded as diagnostic triplets

---

## Stage Details

### S1. Experiment Design
- **Knowledge type:** evaluative
- **Depends on:** (none — entry point)
- **Produces:** FileX (.MZX/.SNX/.SBX) — the master orchestration document
- **Skill document:** `docs/s1_experiment_design_skill.md`
- **Tools:** `validate_filex_structure`
- **Milestones:**
  - FileX exists with valid header and `*EXP.DETAILS` section
  - Treatment table populated with valid factor level cross-references (CU, FL, SA, IC, MP, MI, MF, MR, MC, MT, ME, MH, SM)

### S2. Weather Data Preparation
- **Knowledge type:** procedural
- **Depends on:** (none — parallel with S1, S3, S4)
- **Produces:** `.WTH` daily weather file
- **Skill document:** `docs/s2_weather_prep_skill.md`
- **Tools:** `validate_weather_file`, `calculate_tav_amp`
- **Milestones:**
  - .WTH file exists with correct station code naming (pattern: `[SSSS]YYMM.WTH`)
  - No missing days in simulation period; no -99.0 in SRAD/TMAX/TMIN/RAIN
  - Units correct: SRAD in MJ/m²/day, T in °C, RAIN in mm/day

### S3. Soil Profile Setup
- **Knowledge type:** procedural
- **Depends on:** (none — parallel with S1, S2, S4)
- **Produces:** `.SOL` soil profile file
- **Skill document:** `docs/s3_soil_setup_skill.md`
- **Tools:** `validate_soil_profile`
- **Milestones:**
  - .SOL file contains target soil profile (PEDON code match)
  - Water limits satisfy SLLL < SDUL < SSAT for all layers
  - Layer depths (SLB) monotonically increasing

### S4. Genotype Configuration
- **Knowledge type:** evaluative
- **Depends on:** (none — parallel with S1, S2, S3)
- **Produces:** Cultivar code selection referencing `.CUL`/`.ECO`/`.SPE` files
- **Skill document:** `docs/s4_genotype_config_skill.md`
- **Tools:** (none implemented yet)
- **Milestones:**
  - Cultivar code (INGENO) in FileX matches entry in `.CUL` file
  - Ecotype code (ECO#) referenced by cultivar exists in `.ECO` file

### S5. Simulation Controls
- **Knowledge type:** evaluative
- **Depends on:** S1 (experiment design — needs FileX structure)
- **Produces:** `*SIMULATION CONTROLS` section in FileX
- **Skill document:** `docs/s5_simulation_controls_skill.md`
- **Tools:** (none implemented yet)
- **Milestones:**
  - All method switches have valid values (e.g., MEEVP in {R,P,M,F,D})
  - Start date precedes planting date; NYRS covers simulation period

### S6. Initial Conditions
- **Knowledge type:** evaluative
- **Depends on:** S3 (soil setup — layer depths must match)
- **Produces:** `*INITIAL CONDITIONS` section in FileX
- **Skill document:** `docs/s6_initial_conditions_skill.md`
- **Tools:** (none implemented yet)
- **Milestones:**
  - IC layer depths (ICBL) match soil profile layer depths (SLB)
  - Initial soil water (SH2O) between LL and SAT for each layer

### S7. Management Specification
- **Knowledge type:** evaluative
- **Depends on:** S1 (experiment design — needs treatment structure)
- **Produces:** Management sections in FileX (planting, irrigation, fertilizer, tillage, residue, harvest, environment)
- **Skill document:** `docs/s7_management_spec_skill.md`
- **Tools:** (none implemented yet)
- **Milestones:**
  - Planting date, population, and depth specified
  - All management dates fall within simulation period
  - All method codes (FMCD, IROP, etc.) are valid DSSAT codes

### S8. Batch Execution
- **Knowledge type:** debugging
- **Depends on:** S1, S2, S3, S4, S5, S6, S7 (all preparation stages converge)
- **Produces:** DSSBatch.v48, model outputs (Summary.OUT, PlantGro.OUT, etc.)
- **Skill document:** `docs/s8_batch_execution_skill.md`
- **Tools:** `create_batch_file`
- **Milestones:**
  - `dscsm048` executable exists and is current
  - Batch file references valid FileX and treatment numbers
  - Simulation completed without fatal errors (exit code 0, no FATAL in MODEL.ERR)
  - Expected output files created

### S9. Output Parsing and Evaluation
- **Knowledge type:** procedural
- **Depends on:** S8 (batch execution — needs output files)
- **Produces:** Structured data (parsed Summary.OUT, PlantGro.OUT, Evaluate.OUT)
- **Skill document:** `docs/s9_output_parsing_skill.md`
- **Tools:** `parse_summary_out`
- **Milestones:**
  - Summary.OUT parsed into structured data (HWAH, ADAT, MDAT)
  - Simulated yield is physically reasonable (0 < HWAH < 25000 kg/ha)
  - Phenological dates in expected order (PDAT < ADAT < MDAT)

---

## Dependency Graph

```
Explicit dependencies (solid):
  S1 ──→ S5 (simulation controls need FileX)
  S1 ──→ S7 (management needs treatment structure)
  S3 ──→ S6 (initial conditions must match soil layers)
  S1,S2,S3,S4,S5,S6,S7 ──→ S8 (all converge at execution)
  S8 ──→ S9 (output parsing needs model output)

Implicit dependencies (hidden):
  S2 ←···→ S1  WSTA code in FileX *FIELDS must match .WTH station code
  S3 ←···→ S1  ID_SOIL in FileX *FIELDS must match .SOL PEDON code
  S4 ←···→ S1  INGENO in FileX *CULTIVARS must match .CUL entry
  S4 ←···→ S8  Model-specific coefficients (CERES vs CROPGRO) determined by crop model selection
```

---

## Parallelism

Stages **S1, S2, S3, S4** can begin in parallel — they write to independent files. However, S2/S3/S4 produce codes (WSTA, ID_SOIL, INGENO) that S1 references, so in practice the practitioner often starts S1 last to cross-reference.

Stages **S5, S6, S7** depend on S1 (and S6 depends on S3), but are otherwise independent of each other.

Stage **S8** is the convergence point — all preparation must be complete.

Stage **S9** is strictly sequential after S8.

---

## Key Integration Point: The FileX

The FileX (`.MZX`, `.SNX`, `.SBX`, etc.) is the central orchestration document. It does not contain the data itself but references:
- Weather station code → `.WTH` file
- Soil profile code → `.SOL` file
- Cultivar code → `.CUL`/`.ECO`/`.SPE` files

All management operations, simulation controls, and initial conditions are written directly into FileX sections. The `INPUT_SUB` module (ipexp.for) parses the FileX at runtime and routes data to the DYNAMIC state machine.

---

## Tool Coverage Summary

| Stage | Tools Available | Tools Missing |
|-------|----------------|---------------|
| S1 | validate_filex_structure | create_filex_skeleton |
| S2 | validate_weather_file, calculate_tav_amp | convert_weather_to_wth |
| S3 | validate_soil_profile | convert_soil_to_sol, check_water_limits |
| S4 | — | list_available_cultivars, validate_cultivar_match |
| S5 | — | generate_simulation_controls, validate_switch_consistency |
| S6 | — | generate_initial_conditions, validate_ic_vs_soil |
| S7 | — | generate_management_section, validate_management_dates |
| S8 | create_batch_file | build_dssat, run_dssat, check_model_errors |
| S9 | parse_summary_out | parse_plantgro_out, parse_evaluate_out, compare_sim_obs |

**Coverage: 6/24 tools implemented (25%)**

---

## Diagnostic Triplet Coverage

44 triplets across 24 failure domains, covering all 9 stages. Key domains:
- `file_not_found`, `missing_section`, `string_overflow` (path & format)
- `unit_mismatch`, `silent_default`, `silent_clamp` (silent errors)
- `date_confusion`, `date_ordering`, `parameter_range` (data validity)
- `zero_yield`, `numerical_instability`, `infinite_loop` (runtime)
- `build_failure`, `runtime_crash`, `array_overflow` (execution)

See `diagnostics/triplets.yaml` for full lookup table.
