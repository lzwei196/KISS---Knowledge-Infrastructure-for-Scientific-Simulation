# Knowledge Dissection Toolkit (KDT) v4.0

> **"Real Binary, Real Grid, Real Data"**

The Knowledge Dissection Toolkit is a methodology and software library for
systematically extracting operational knowledge from Earth science models and
packaging it into structured **knowledge infrastructure** (KI) that enables
autonomous model operation.

KDT was developed to address a fundamental problem: running complex
environmental models requires vast tacit knowledge -- unit conventions,
file format quirks, compilation tricks, input data requirements -- that exists
only in the heads of experienced modellers. KDT makes this knowledge explicit,
machine-readable, and testable.

## Philosophy

KDT is built on three non-negotiable principles:

1. **Real Binary** -- Run the actual model software (compiled Fortran binary,
   native package), not a Python surrogate or analytic reimplementation. The
   goal is to capture the knowledge needed to operate the *real* model.

2. **Real Grid** -- Run models in their intended distributed/gridded mode
   (not lumped basin-average). Gridded forcing data exists; use it.

3. **Real Data** -- Validate with independently prepared forcing and
   observation data, not developer-bundled test cases. Developer data proves
   the binary works; your own data proves the knowledge infrastructure works.

## The 9-Stage Dissection Pipeline

KDT processes each model through nine stages:

| Stage | Name | What It Does |
|-------|------|-------------|
| s0 | **Acquire** | Clone source code, detect language and build system |
| s1 | **Pipeline Map** | Scan I/O operations, extract workflow from documentation |
| s2 | **Unit Discovery** | Identify all variables, their units, and required conversions |
| s3 | **Tool Generation** | Create Python wrapper tools for data preparation |
| s4 | **Skill Documentation** | Write SKILL.md and supporting documentation |
| s5 | **Triplet Construction** | Build error-diagnosis-remedy diagnostic triplets |
| s6 | **Assembly** | Package everything into the final KI structure |
| s7 | **Binary Test** | Build and run with developer test data |
| s8 | **Validation** | Run against real observations, compute performance metrics |

Stages s0-s1 are automated Python scripts. Stages s2-s8 are guided by an AI
agent with full filesystem access, following domain-specific protocols.

## The 3-Step Validation Protocol

Every model must pass three validation steps (see `VALIDATION_PROTOCOL.md`):

1. **Developer Data Test** -- Verify the model binary executes correctly using
   the developers' own example data. This proves the binary works.

2. **Progressive Data Replacement** -- Systematically replace developer data
   with your own data (forcing, soil, land cover, DEM, etc.), one component
   at a time. This isolates which tool/conversion has a bug.

3. **Full Autonomous Run** -- Run the model entirely on your own data and
   verify physically reasonable results. This proves the knowledge
   infrastructure works.

## Knowledge Infrastructure (KI) Package Structure

Each dissected model produces a KI package with this structure:

```
ki/
  SKILL.md            # Operational skill document (14 required sections)
  tools/              # Python scripts for data preparation
    convert_forcing.py
    build_soil_params.py
    run_model.py
    ...
  docs/               # Supporting documentation
    input_format.md
    compilation_notes.md
    ...
  diagnostics/        # Error knowledge
    triplets.yaml     # Error-diagnosis-remedy triplets
    error_log.yaml    # Chronological error history
```

## What This Package Contains

| Directory | Contents |
|-----------|----------|
| `ki_tools_common/` | Shared utility library: unit conversions, humidity, NetCDF helpers, validation, metrics, I/O, forcing-source metadata |
| `validators/` | Pre-simulation data quality checkers |
| `templates/` | Templates for SKILL.md, stage logs, diagnostic triplets, validation sheets, and KI schemas |
| `pipeline/` | Guides for the 9-stage pipeline, agent prompts, and data registries |
| `examples/` | Self-contained worked examples |

## Quick Start

```bash
# Install the shared library
cd ki_tools_common
pip install -e .            # minimal (numpy only)
pip install -e ".[all]"     # with xarray, netCDF4, geopandas

# Run unit tests
pip install -e ".[dev]"
pytest tests/ -v

# Check your forcing data for unit errors
python ../validators/preflight_forcing.py /path/to/your/forcing/

# Compute cal/val metrics
python -c "
from ki_tools_common.metrics import all_metrics
import numpy as np
obs = np.random.rand(365) * 100
sim = obs * 1.05 + np.random.randn(365) * 5
print(all_metrics(obs, sim))
"
```

## Requirements

- Python >= 3.8
- numpy >= 1.20
- Optional: xarray, netCDF4, geopandas, shapely, pandas, scipy
- Optional: pytest (for running tests)

## Citation

If you use KDT in your research, please cite:

```bibtex
@article{zhang2026kdt,
  title   = {Knowledge Dissection Toolkit: Systematic Extraction of Operational
             Knowledge from Earth Science Models},
  author  = {Zhang, Jianyun and [AUTHORS]},
  journal = {[JOURNAL]},
  year    = {2026},
  doi     = {[DOI]}
}
```

## License

MIT License. See `LICENSE` for details.

---

*Developed by the Jianyun Zhang Research Group, Hohai University.*
