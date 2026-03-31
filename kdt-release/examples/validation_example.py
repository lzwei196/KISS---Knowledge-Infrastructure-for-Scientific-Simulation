#!/usr/bin/env python3
"""
validation_example.py -- Demonstrates metrics computation and cal/val split.

This self-contained example shows how to:
1. Compute all standard performance metrics (NSE, KGE, PBIAS, RMSE, r)
2. Split data into calibration and validation periods
3. Detect potential data leakage
4. Use the standard_result output format

No external data files are needed -- the example uses synthetic data.

Usage:
    python validation_example.py
"""

import datetime
import numpy as np

# ---------------------------------------------------------------------------
# 1. Generate synthetic discharge data
# ---------------------------------------------------------------------------

print("=" * 60)
print("  KDT Validation Example")
print("=" * 60)

np.random.seed(42)

# Generate 10 years of daily data
start_date = datetime.date(1981, 1, 1)
n_days = 365 * 10 + 3   # ~10 years with leap days
dates = [start_date + datetime.timedelta(days=i) for i in range(n_days)]

# Synthetic "observed" discharge: seasonal pattern + noise
t = np.arange(n_days)
obs = 500 + 400 * np.sin(2 * np.pi * t / 365.25 - np.pi / 2) \
    + np.random.normal(0, 80, n_days)
obs = np.maximum(obs, 10)  # no negative discharge

# Synthetic "simulated" discharge: biased version of obs
sim = obs * 1.08 + np.random.normal(0, 50, n_days)
sim = np.maximum(sim, 0)

print(f"\nGenerated {n_days} days of synthetic data ({dates[0]} to {dates[-1]})")
print(f"  Observed mean:  {np.mean(obs):.1f} m3/s")
print(f"  Simulated mean: {np.mean(sim):.1f} m3/s")

# ---------------------------------------------------------------------------
# 2. Compute metrics on the full period
# ---------------------------------------------------------------------------

from ki_tools_common.metrics import nse, kge, pbias, rmse, pearson_r, all_metrics

print("\n--- Full-period metrics ---")
m = all_metrics(obs, sim)
for key, val in m.items():
    print(f"  {key:>6s} = {val:.4f}")

# ---------------------------------------------------------------------------
# 3. Split into calibration and validation periods
# ---------------------------------------------------------------------------

# Import the cal/val helper and configure custom periods
import sys
sys.path.insert(0, '..')
try:
    from validators.standard_calval import (
        set_periods, split_data, compute_calval_metrics,
    )
except ImportError:
    # Fallback: add parent directory
    sys.path.insert(0, '.')
    from validators.standard_calval import (
        set_periods, split_data, compute_calval_metrics,
    )

# Configure periods for our synthetic data
set_periods(
    spinup_year=1981,             # discard first year
    cal_start='1982-01-01',
    cal_end='1986-12-31',         # 5 years calibration
    val_start='1987-01-01',
    val_end='1990-12-31',         # 4 years validation
)

print("\n--- Cal/Val split metrics ---")
calval = compute_calval_metrics(dates, obs, sim)

for period_name, period_metrics in calval.items():
    print(f"\n  {period_name.upper()}:")
    for key, val in period_metrics.items():
        print(f"    {key:>6s} = {val}")

# ---------------------------------------------------------------------------
# 4. Demonstrate what data leakage looks like
# ---------------------------------------------------------------------------

print("\n--- Data leakage demonstration ---")
print("  (What happens if you report full-period metrics as 'validation')")

nse_cal = calval['calibration']['NSE']
nse_val = calval['validation']['NSE']
nse_full = calval['full']['NSE']

print(f"  NSE (calibration only):  {nse_cal:.4f}")
print(f"  NSE (validation only):   {nse_val:.4f}")
print(f"  NSE (full period):       {nse_full:.4f}")
print(f"\n  Difference (full - val): {nse_full - nse_val:+.4f}")
print("  In real models with calibration, this difference is typically")
print("  0.10-0.15 -- a significant inflation of apparent skill.")

# ---------------------------------------------------------------------------
# 5. Validate discharge data before computing metrics
# ---------------------------------------------------------------------------

from ki_tools_common.validation import validate_discharge

print("\n--- Pre-metric validation checks ---")

# Normal case
warnings = validate_discharge(sim, obs)
if warnings:
    for w in warnings:
        print(f"  WARNING: {w}")
else:
    print("  Discharge data passes validation checks.")

# Pathological case: wrong units (1000x too high)
print("\n  What if sim is in wrong units?")
sim_wrong = sim * 1000  # accidentally in L/s instead of m3/s
warnings = validate_discharge(sim_wrong, obs)
for w in warnings:
    print(f"  WARNING: {w}")

# ---------------------------------------------------------------------------
# 6. Standard output format
# ---------------------------------------------------------------------------

from ki_tools_common.io_helpers import standard_result

print("\n--- Standard output format ---")
result = standard_result(
    status="success",
    warnings=["Validation period shorter than calibration period"],
    metrics={
        "NSE_cal": nse_cal,
        "NSE_val": nse_val,
        "KGE_cal": calval['calibration']['KGE'],
        "KGE_val": calval['validation']['KGE'],
        "PBIAS_val": calval['validation']['PBIAS'],
    },
    outputs={
        "hydrograph": "figures/hydrograph_calval.png",
        "stage_log": "stage_log.json",
    },
)

import json
print(json.dumps(result, indent=2))

# ---------------------------------------------------------------------------
# 7. Monthly aggregation
# ---------------------------------------------------------------------------

from ki_tools_common.metrics import monthly_metrics

print("\n--- Monthly aggregated metrics ---")
dates_np = np.array(dates, dtype='datetime64[D]')
m_monthly = monthly_metrics(obs, sim, dates_np)
for key, val in m_monthly.items():
    print(f"  {key:>6s} = {val:.4f}")
print("  (Monthly aggregation typically improves metrics by smoothing noise)")

print("\n" + "=" * 60)
print("  Example complete.")
print("  Key takeaway: ALWAYS report separate cal/val metrics.")
print("=" * 60)
