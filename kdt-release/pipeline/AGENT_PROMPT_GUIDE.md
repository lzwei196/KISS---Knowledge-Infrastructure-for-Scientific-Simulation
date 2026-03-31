# Agent Prompt Guide -- Writing Dissection Prompts for AI Agents

This document describes how to write effective prompts for AI agents performing
model dissection. Agents handle stages s2-s8, which require deep analysis of
source code, file formats, and data.

---

## Prompt Architecture

A dissection prompt has four sections:

### 1. Context Block

Provide the agent with:
- Model name, version, domain
- Source code location
- Probe report from s0 (language, build system, file counts)
- Pipeline map from s1 (I/O operations, workflow)
- Available data sources and their paths
- Target test basin and observation data

```
You are dissecting [MODEL_NAME] v[VERSION], a [DOMAIN] model written in
[LANGUAGE] with a [BUILD_SYSTEM] build system.

Source code: [PATH]
Probe report: [PATH_TO_probe_report.json]
```

### 2. Phase Instructions

Tell the agent which phase to execute. A typical decomposition:

**Phase 1: Discovery and Analysis (s2)**
- Read source code to find all input variables and their units
- Read example input files to verify formats
- Cross-reference with data source documentation
- Produce the unit conversion table

**Phase 2: Build (s3, s7)**
- Compile the model from source
- Fix any build errors (document as triplets)
- Run the developer example
- Verify output against expected results

**Phase 3: Tool Development (s3, s4)**
- Write data preparation tools using ki_tools_common
- Follow the copy-first approach for control files
- Write SKILL.md and supporting documentation
- Write diagnostic triplets for errors encountered

**Phase 4: Validation (s8)**
- Run progressive data replacement
- Run full autonomous validation
- Compute cal/val metrics
- Write validation sheet

### 3. Policy Block

Embed critical rules that prevent common mistakes:

```
CRITICAL POLICIES:
1. REAL BINARY ONLY -- You MUST run the actual model binary, not a Python
   reimplementation. If the build fails, fix the build.
2. UNIT VERIFICATION -- For EVERY input variable, read the actual file
   attributes to verify units. NEVER trust documentation alone.
3. COPY-FIRST -- Never generate control files from scratch. Copy from a
   working example and modify values.
4. CAL/VAL SPLIT -- If calibrating, use separate calibration and validation
   periods. NEVER report metrics on calibration data as "validation".
5. DISTRIBUTED MODE -- Run gridded models in distributed mode, not lumped.
```

### 4. Data Awareness Block

Provide forcing data source information:

```
FORCING DATA SOURCES:
- [DATASET_1]: [PATH], [RESOLUTION], [TEMPORAL], [VARIABLES_AND_UNITS]
- [DATASET_2]: [PATH], [RESOLUTION], [TEMPORAL], [VARIABLES_AND_UNITS]

UNIT WARNING: [DATASET_1] precipitation is stored as kg/m2/s (NOT mm/day).
Always verify by reading the actual NetCDF attributes.

OBSERVATION DATA:
- [OBS_DATASET]: [PATH], [VARIABLES], [PERIOD]
```

---

## Prompt Template

```
# Model Dissection: [MODEL_NAME]

## Context
- Model: [MODEL_NAME] v[VERSION]
- Domain: [DOMAIN]
- Language: [LANGUAGE]
- Source: [PATH]
- Work directory: [WORK_DIR]

## Your Task
Execute Phase [N] of the dissection pipeline for [MODEL_NAME].

[PHASE-SPECIFIC INSTRUCTIONS]

## Data Sources
[DATA AWARENESS BLOCK]

## Policies
[POLICY BLOCK]

## Deliverables
When complete, update stage_log.json with:
- Stage status: "completed"
- Key metrics and outputs
- Any errors encountered

Files to create/update:
- [LIST OF EXPECTED OUTPUT FILES]
```

---

## Anti-Patterns in Agent Prompts

1. **Vague instructions**: "Set up the model" is too vague. Specify: "Compile
   the Fortran source using `make`, then run the `example_1/` test case and
   verify discharge output matches `expected_output.txt` within 1%."

2. **Missing unit context**: Always include the data source unit table. Agents
   that lack this context will assume mm/day for precipitation when the data
   may be kg/m2/s.

3. **No success criteria**: Define what "done" looks like. "Model runs" is
   insufficient. "Model produces daily discharge >0 and <10000 m3/s for all
   timesteps, with NSE > 0 against observed data" is a success criterion.

4. **No error recovery path**: Tell the agent what to do when things fail.
   "If compilation fails on ESMF, check if ESMF is installed at [PATH]. If
   not, build ESMF first using [INSTRUCTIONS]."

5. **Assuming the agent knows your server**: Always provide absolute paths
   to data, libraries, and tools. Never assume the agent knows where things
   are stored.

---

## Phase-Specific Tips

### For Build Phases
- Provide the exact compiler and version available
- List pre-installed libraries and their paths
- Note any non-standard environment modules
- Give the agent permission to install missing dependencies

### For Validation Phases
- Provide the observation data path and format
- Specify the calibration and validation periods
- Define the minimum acceptable metrics
- Tell the agent to use `validators/preflight_forcing.py` before running

### For Documentation Phases
- Point the agent to `templates/SKILL_TEMPLATE.md` as the target structure
- Require the unit conversion table (Section 8)
- Require at least 5 diagnostic triplets

---

*Part of the Knowledge Dissection Toolkit by the Jianyun Zhang Research Group,
Hohai University.*
