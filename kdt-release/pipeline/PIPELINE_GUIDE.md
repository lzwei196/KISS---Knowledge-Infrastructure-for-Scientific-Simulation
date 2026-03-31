# Pipeline Guide -- The 9-Stage Dissection Process

This document describes how the Knowledge Dissection Toolkit processes a model
from source code to validated knowledge infrastructure. Each stage has defined
inputs, outputs, and completion criteria.

---

## Overview

```
s0 Acquire --> s1 Pipeline Map --> s2 Unit Discovery --> s3 Tool Generation
    --> s4 Skill Documentation --> s5 Triplet Construction --> s6 Assembly
    --> s7 Binary Test --> s8 Validation
```

Stages s0-s1 are automated Python scripts that can run in parallel across
many models. Stages s2-s8 require deeper analysis and are typically guided
by an AI agent or human expert with full filesystem access.

---

## Stage 0: Acquire

**Purpose**: Obtain model source code and probe its structure.

**Inputs**:
- Git repository URL or local source archive
- Model name and domain classification

**Process**:
1. Clone repository (shallow, `--depth 1`) or extract archive
2. Run file census: count files by extension, detect languages
3. Identify build system (CMake, Make, configure, pip, etc.)
4. Locate documentation files (README, manuals, examples)
5. Detect example/test data

**Outputs**:
- `source/` -- Cloned source code
- `probe_report.json` -- Language breakdown, build system, file counts,
  presence of examples

**Completion criteria**: Source code available locally, probe report generated.

---

## Stage 1: Pipeline Map

**Purpose**: Understand the model's data flow -- what goes in, what comes out,
and how.

**Inputs**:
- Source code from s0
- Domain template (provides expected pipeline structure)

**Process**:
1. Scan source for I/O operations (file reads/writes, NetCDF calls)
2. Extract workflow from documentation (README, user guide, tutorials)
3. Match against domain-specific templates
4. Generate initial knowledge infrastructure YAML

**Outputs**:
- `knowledge_infrastructure.yaml` -- Pipeline structure and variable list
- `workflow.md` -- Human-readable workflow description

**Completion criteria**: I/O operations catalogued, preliminary pipeline mapped.

---

## Stage 2: Unit Discovery

**Purpose**: Identify every variable the model reads, the units it expects,
and the units your data provides.

**Inputs**:
- Source code (particularly FORMAT statements, variable declarations)
- Documentation and example files
- Your forcing data source specifications

**Process**:
1. Grep source for unit strings, conversion factors, FORMAT statements
2. Read example input files to verify units
3. Cross-reference with forcing data attributes
4. Build the conversion table (source unit -> model unit -> factor)

**Outputs**:
- Unit conversion table in SKILL.md Section 8
- Conversion factors embedded in tool scripts

**Completion criteria**: Every input variable has a documented (source_unit,
model_unit, conversion_factor) triple, verified against actual file attributes.

**Key risk**: This is where 37% of all silent errors originate. NEVER trust
documentation alone. Always verify by reading the actual data file:
```python
import xarray as xr
ds = xr.open_dataset('file.nc')
print(ds['variable'].attrs)  # This is ground truth
```

---

## Stage 3: Tool Generation

**Purpose**: Create Python scripts that automate data preparation.

**Inputs**:
- Unit conversion table from s2
- Input file format specifications
- Example/template input files

**Process**:
1. Write `convert_forcing.py` -- forcing data conversion with verified units
2. Write `build_soil_params.py` -- soil/subsurface parameter extraction
3. Write `build_domain.py` -- domain setup (DEM, grid, routing)
4. Write any model-specific tools (landcover, initial conditions, etc.)

**Design rules**:
- Every tool follows the **validate-process-validate** pattern
- Every tool uses `ki_tools_common` for unit conversions
- Every tool uses the **copy-first** approach for control files
- Every tool outputs a standard JSON result (`io_helpers.standard_result`)
- Minimum 3 tools per model

**Outputs**:
- `ki/tools/*.py` -- Data preparation scripts

**Completion criteria**: Tools exist for all input components, each produces
correctly formatted model input.

---

## Stage 4: Skill Documentation

**Purpose**: Write comprehensive operational documentation.

**Inputs**:
- All knowledge gathered in s0-s3
- Model documentation and user guides
- Error experiences from tool development

**Process**:
1. Write `ki/SKILL.md` with all 14 required sections (see
   `templates/SKILL_TEMPLATE.md`)
2. Write supporting documentation in `ki/docs/`
3. Document all build issues, platform notes, and configuration details

**Outputs**:
- `ki/SKILL.md` -- Primary operational skill document
- `ki/docs/*.md` -- Supporting documentation (minimum 3 files)

**Completion criteria**: SKILL.md has all 14 sections populated, including the
unit conversion table and tool inventory.

---

## Stage 5: Triplet Construction

**Purpose**: Capture error knowledge in structured, reusable form.

**Inputs**:
- All errors encountered during s0-s4
- Error logs from attempted runs
- Common failure patterns database

**Process**:
1. Review all errors, warnings, and surprises from prior stages
2. Structure each as an error-diagnosis-remedy triplet
3. Classify by category (unit_conversion, format_error, etc.)
4. Tag as silent or non-silent
5. Cross-reference with common failure patterns

**Outputs**:
- `ki/diagnostics/triplets.yaml` -- Structured error knowledge
- `ki/diagnostics/error_log.yaml` -- Chronological error history

**Completion criteria**: All significant errors captured as triplets, with
at least the most dangerous errors (silent ones) documented.

---

## Stage 6: Assembly

**Purpose**: Package everything into the final KI structure.

**Inputs**:
- All outputs from s0-s5

**Process**:
1. Verify directory structure matches the KI schema
2. Check all tools are present and have correct imports
3. Verify SKILL.md references match actual files
4. Run a dry-run import test on all Python tools
5. Verify `knowledge_infrastructure.yaml` is complete

**Outputs**:
- Complete `ki/` directory with validated structure

**Completion criteria**: KI package is self-contained and internally
consistent.

---

## Stage 7: Binary Test

**Purpose**: Verify the model binary executes correctly (Step 1 of the
validation protocol).

**Inputs**:
- Model binary (compiled or installed)
- Developer example/test data

**Process**:
1. Build the model from source (if compiled)
2. Run the developer example exactly as documented
3. Verify output matches expected results
4. Record runtime, memory usage, and any issues

**Outputs**:
- Updated `stage_log.json` with s7 results
- Build notes in SKILL.md Section 4
- Diagnostic triplets for any build issues

**Completion criteria**: Model runs to completion with developer data,
output matches expected values. This is validation Step 1 ("binary_only").

---

## Stage 8: Validation

**Purpose**: Validate the knowledge infrastructure by running the model
entirely on pipeline-prepared data (Steps 2 and 3 of the validation protocol).

**Inputs**:
- Model binary from s7
- KI tools from s3
- Your forcing, soil, landcover, DEM, and observation data

**Process**:
1. **Progressive replacement** (Step 2):
   - Replace forcing with your data, run, verify
   - Replace soil with your data, run, verify
   - Continue for all components, one at a time
2. **Full autonomous run** (Step 3):
   - All inputs from your pipeline (zero developer data)
   - Run on your standard test basin
   - Compute NSE, KGE, PBIAS, r for calibration and validation periods
   - Check physical reasonableness

**Outputs**:
- Updated `stage_log.json` with full metrics
- Validation sheet (see `templates/validation_sheet_template.md`)
- Updated SKILL.md Section 11 (Validated Results)
- Additional diagnostic triplets for any errors found

**Completion criteria**: Model achieves `production_validated` status --
all inputs from pipeline data, physically reasonable results, proper cal/val
split.

---

## Stage Completion Summary

| Stage | Key Deliverable | Typical Duration |
|-------|----------------|-----------------|
| s0 | `probe_report.json` | Minutes |
| s1 | `knowledge_infrastructure.yaml` | Minutes |
| s2 | Unit conversion table | 1-4 hours |
| s3 | `ki/tools/*.py` (3+ scripts) | 2-8 hours |
| s4 | `ki/SKILL.md` + docs | 1-3 hours |
| s5 | `ki/diagnostics/triplets.yaml` | 1-2 hours |
| s6 | Complete `ki/` package | 30 minutes |
| s7 | Binary test passed | 1-8 hours |
| s8 | Production validated | 2-16 hours |

Total: approximately 1-3 days per model for an experienced operator, depending
on model complexity.

---

*Part of the Knowledge Dissection Toolkit by the Jianyun Zhang Research Group,
Hohai University.*
