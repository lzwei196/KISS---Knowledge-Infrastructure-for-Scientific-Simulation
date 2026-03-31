# Data Registry Guide -- Organizing Institutional Datasets for KDT

This document describes how to create a data registry for your server or
institution. The data registry maps available datasets to their locations,
variables, units, and coverage, enabling the dissection pipeline to
automatically select appropriate data sources for each model.

---

## Purpose

Without a data registry, every model dissection must manually locate data
files, verify units, and document paths. A centralized registry eliminates
this repeated work and ensures consistency across models.

---

## Registry Structure

Create a YAML file (e.g., `data_registry/datasets.yaml`) with this structure:

```yaml
# Data Registry for [YOUR_INSTITUTION]
# Last updated: [DATE]

forcing:
  # Each entry describes one forcing dataset
  - name: "[DATASET_NAME]"
    description: "[Brief description]"
    path: "[/absolute/path/to/data/]"
    resolution:
      spatial: "[0.25 deg / 0.1 deg / point / varies]"
      temporal: "[daily / 3-hourly / hourly / monthly]"
    coverage:
      spatial: "[Global / Regional name / Country]"
      temporal: "[START_YEAR - END_YEAR]"
    variables:
      - name: "precipitation"
        file_variable: "[prec / tp / P / ...]"
        unit: "[kg/m2/s / mm/day / m/accumulated / ...]"
        conversions:
          "mm/day": 86400.0    # multiply by this to get mm/day
          "mm/hr": 3600.0
      - name: "temperature"
        file_variable: "[temp / t2m / Tair / ...]"
        unit: "[K / degC]"
        conversions:
          "degC": -273.15      # additive: add this to get degC
      # ... all variables
    format: "[NetCDF / CSV / GRIB / HDF5]"
    file_pattern: "[*{variable}*{year}*.nc]"
    notes: "[Any important notes, e.g., 'precipitation documented as mm/day but actually kg/m2/s']"

observations:
  - name: "[OBSERVATION_DATASET]"
    type: "[discharge / soil_moisture / snow / crop_yield / ...]"
    path: "[/absolute/path/to/data/]"
    stations:
      - id: "[STATION_ID]"
        name: "[STATION_NAME]"
        location: [LAT, LON]
        basin_area_km2: [AREA]
        period: "[START - END]"
        variables: ["discharge_m3s"]
    format: "[CSV / NetCDF / text]"

static:
  soil:
    - name: "[SOIL_DATABASE]"
      path: "[/absolute/path/]"
      variables: ["sand_pct", "clay_pct", "silt_pct", "bulk_density", "Ksat", "porosity"]
      resolution: "[RESOLUTION]"
      coverage: "[Global / Regional]"
      format: "[NetCDF / Raster / MDB / Shapefile]"

  landcover:
    - name: "[LANDCOVER_DATASET]"
      path: "[/absolute/path/]"
      resolution: "[1 km / 500 m / 30 m]"
      classification: "[IGBP / CCI / NLCD / ...]"
      year: "[YEAR or range]"

  topography:
    - name: "[DEM_DATASET]"
      path: "[/absolute/path/]"
      resolution: "[90 m / 30 m / 1 arcsec]"
      vertical_datum: "[WGS84 / EGM96 / ...]"
      coverage: "[Global / Regional]"
```

---

## Registry Design Principles

### 1. Absolute Paths Only

Always use absolute paths. Relative paths break when scripts are called from
different working directories.

### 2. Units Are Ground Truth

The `unit` field in the registry MUST match the actual file attributes, not
the documentation. Verify with:

```python
import xarray as xr
ds = xr.open_dataset('/path/to/data/sample.nc')
for v in ds.data_vars:
    print(f"{v}: {ds[v].attrs.get('units', 'NO UNIT ATTR')}")
```

### 3. Conversion Factors Are Explicit

For each variable, list the conversion factor to common target units. This
prevents every tool from independently computing (and potentially getting
wrong) the conversion.

### 4. Document the Traps

If a dataset has known issues (e.g., "documented as mm/day but actually
kg/m2/s"), note this explicitly in the `notes` field. This prevents future
users from falling into the same trap.

### 5. Tier Your Data

Organize datasets by reliability tier:

| Tier | Description | Example |
|------|-------------|---------|
| Tier 1 | Gold standard, well-validated | Station observations |
| Tier 2 | Reanalysis/remote sensing, good coverage | ERA5, CMFD |
| Tier 3 | Global defaults, moderate quality | HWSD, AVHRR |
| Tier 4 | Literature/estimated values | Default parameters |

---

## Example: Selecting Data for a Model

When preparing data for a new model, the selection logic is:

1. **Forcing**: Choose based on model's temporal resolution requirement.
   If the model needs sub-daily data, use a sub-daily dataset. If daily
   suffices, use the highest-resolution daily product available.

2. **Observations**: Choose the station closest to / within the test basin,
   with the longest overlap with the forcing data period.

3. **Static data**: Use the highest-resolution available product that covers
   the study domain.

```python
# Pseudocode for data selection
def select_forcing(model_timestep, study_region):
    if model_timestep < "daily":
        candidates = [d for d in registry.forcing
                      if d.temporal in ("3-hourly", "hourly")
                      and d.coverage.includes(study_region)]
    else:
        candidates = [d for d in registry.forcing
                      if d.coverage.includes(study_region)]
    # Prefer highest spatial resolution
    return sorted(candidates, key=lambda d: d.resolution)[0]
```

---

## Validation Script

After creating your registry, validate it:

```python
#!/usr/bin/env python3
"""Validate that all paths in the data registry exist."""
import yaml
from pathlib import Path

with open("data_registry/datasets.yaml") as f:
    registry = yaml.safe_load(f)

errors = []
for section in ("forcing", "observations"):
    for ds in registry.get(section, []):
        path = Path(ds["path"])
        if not path.exists():
            errors.append(f"MISSING: {ds['name']} at {ds['path']}")
        else:
            # Check for at least one data file
            nc_files = list(path.glob("*.nc")) + list(path.glob("**/*.nc"))
            csv_files = list(path.glob("*.csv"))
            if not nc_files and not csv_files:
                errors.append(f"EMPTY: {ds['name']} at {ds['path']}")

if errors:
    print(f"Registry validation: {len(errors)} errors")
    for e in errors:
        print(f"  {e}")
else:
    print("Registry validation: all paths exist")
```

---

*Part of the Knowledge Dissection Toolkit by the Jianyun Zhang Research Group,
Hohai University.*
