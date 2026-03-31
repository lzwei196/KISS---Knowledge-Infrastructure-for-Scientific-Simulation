#!/usr/bin/env python3
"""
unit_conversion_example.py -- Demonstrates ki_tools_common for forcing data conversion.

This self-contained example shows how to:
1. Use named conversion constants and functions
2. Use the universal convert() dispatcher
3. Apply unit-trap validation to catch common errors
4. Look up conversion factors from the forcing source registry

No external data files are needed -- the example uses synthetic data.

Usage:
    python unit_conversion_example.py
"""

import numpy as np

# ---------------------------------------------------------------------------
# 1. Direct conversion functions
# ---------------------------------------------------------------------------
from ki_tools_common.units import (
    kgm2s_to_mmday,
    kelvin_to_celsius,
    pa_to_hpa,
    wm2_to_mjm2day,
    ms_to_kmh,
    mmday_to_mday,
    CMFD_PRECIP_KGM2S_TO_MMDAY,
)

print("=" * 60)
print("  KDT Unit Conversion Example")
print("=" * 60)

# Simulate CMFD-like forcing data (one day, one grid cell)
# CMFD stores precipitation as kg/m2/s -- this is the #1 unit trap!
precip_kgm2s = 2.315e-5   # typical value: ~2 mm/day
temp_k = 293.15            # 20 degC in Kelvin
pressure_pa = 98500.0      # ~985 hPa
radiation_wm2 = 245.0      # shortwave radiation
wind_ms = 3.5              # wind speed

print("\n--- Raw forcing data (as stored in file) ---")
print(f"  Precipitation:  {precip_kgm2s:.6e} kg/m2/s")
print(f"  Temperature:    {temp_k:.2f} K")
print(f"  Pressure:       {pressure_pa:.0f} Pa")
print(f"  Radiation:      {radiation_wm2:.1f} W/m2")
print(f"  Wind:           {wind_ms:.1f} m/s")

# Convert to common model units
precip_mmday = kgm2s_to_mmday(precip_kgm2s)
temp_c = kelvin_to_celsius(temp_k)
pressure_hpa = pa_to_hpa(pressure_pa)
radiation_mjm2day = wm2_to_mjm2day(radiation_wm2)
wind_kmh = ms_to_kmh(wind_ms)

print("\n--- Converted to common model units ---")
print(f"  Precipitation:  {precip_mmday:.2f} mm/day")
print(f"  Temperature:    {temp_c:.2f} degC")
print(f"  Pressure:       {pressure_hpa:.2f} hPa")
print(f"  Radiation:      {radiation_mjm2day:.2f} MJ/m2/day")
print(f"  Wind:           {wind_kmh:.1f} km/h")

# Model-specific conversion (e.g., lake model needs m/day for rain)
precip_mday = mmday_to_mday(precip_mmday)
print(f"\n  Lake model rain: {precip_mday:.6f} m/day  (from {precip_mmday:.2f} mm/day)")

# ---------------------------------------------------------------------------
# 2. Universal convert() dispatcher
# ---------------------------------------------------------------------------
from ki_tools_common.units import convert

print("\n--- Universal convert() dispatcher ---")
print(f"  25 degC -> K:   {convert(25.0, 'C', 'K', 'temperature'):.2f}")
print(f"  1 kg/m2/s -> mm/day: {convert(1.0, 'kg/m2/s', 'mm/day', 'precipitation'):.0f}")
print(f"  101325 Pa -> atm: {convert(101325.0, 'Pa', 'atm', 'pressure'):.4f}")
print(f"  300 W/m2 -> MJ/m2/day: {convert(300.0, 'W/m2', 'MJ/m2/day', 'radiation'):.2f}")

# Works with numpy arrays too
temps_c = np.array([-10.0, 0.0, 15.0, 25.0, 35.0])
temps_k = convert(temps_c, 'C', 'K', 'temperature')
print(f"\n  Array conversion: {temps_c} degC -> {temps_k} K")

# ---------------------------------------------------------------------------
# 3. Unit-trap validation
# ---------------------------------------------------------------------------
from ki_tools_common.validation import validate_forcing_ranges

print("\n--- Unit-trap validation ---")

# Case A: Correct units (should pass)
print("\nCase A: Correctly converted data")
warnings = validate_forcing_ranges({
    'temperature': np.array([280.0, 290.0, 300.0]),   # K -- correct
    'precipitation': np.array([0.0, 5.0, 20.0]),      # mm/day -- correct
})
if warnings:
    for w in warnings:
        print(f"  WARNING: {w}")
else:
    print("  All checks passed!")

# Case B: Common mistake -- precipitation still in kg/m2/s
print("\nCase B: Precipitation NOT converted (still in kg/m2/s)")
warnings = validate_forcing_ranges({
    'precipitation': np.array([0.0, 1e-5, 3e-5]),     # kg/m2/s -- WRONG for mm/day
})
for w in warnings:
    print(f"  WARNING: {w}")

# Case C: Temperature in Celsius when Kelvin expected
print("\nCase C: Temperature in Celsius instead of Kelvin")
warnings = validate_forcing_ranges({
    'temperature': np.array([15.0, 20.0, 25.0]),      # degC -- WRONG for K
})
for w in warnings:
    print(f"  WARNING: {w}")

# ---------------------------------------------------------------------------
# 4. Forcing source registry
# ---------------------------------------------------------------------------
from ki_tools_common.forcing_sources import (
    get_conversion_factor,
    is_additive_conversion,
    CMFD_VARIABLES,
)

print("\n--- Forcing source registry ---")
print(f"\n  CMFD precipitation unit: {CMFD_VARIABLES['prec']['unit']}")
print(f"  CMFD -> mm/day factor:   {get_conversion_factor('CMFD', 'prec', 'mm/day')}")
print(f"  CMFD -> mm/hr factor:    {get_conversion_factor('CMFD', 'prec', 'mm/hr')}")
print(f"  CMFD -> m/day factor:    {get_conversion_factor('CMFD', 'prec', 'm/day')}")

print(f"\n  CMFD temp unit:          {CMFD_VARIABLES['temp']['unit']}")
print(f"  CMFD temp -> degC:       {get_conversion_factor('CMFD', 'temp', 'degC')}"
      f"  (additive: {is_additive_conversion('CMFD', 'temp', 'degC')})")

print(f"\n  ERA5 precip unit:        m/accumulated")
print(f"  ERA5 tp -> mm/day:       {get_conversion_factor('ERA5', 'tp', 'mm/day')}")

# ---------------------------------------------------------------------------
# 5. Humidity conversions
# ---------------------------------------------------------------------------
from ki_tools_common.humidity import (
    saturation_vapor_pressure,
    specific_humidity_to_rh,
    vpd_from_temp_rh,
    dewpoint_from_rh,
)

print("\n--- Humidity conversions ---")
temp_c_example = 25.0
rh_example = 60.0

es = saturation_vapor_pressure(temp_c_example)
vpd = vpd_from_temp_rh(temp_c_example, rh_example)
td = dewpoint_from_rh(temp_c_example, rh_example)

print(f"  At {temp_c_example} degC, RH={rh_example}%:")
print(f"    Saturation vapor pressure: {es:.2f} hPa")
print(f"    VPD: {vpd:.2f} hPa")
print(f"    Dewpoint: {td:.1f} degC")

# Convert specific humidity to RH (common in reanalysis data)
q_kgkg = 0.01  # 10 g/kg
rh_computed = specific_humidity_to_rh(q_kgkg, 293.15, 101325.0)
print(f"\n  q={q_kgkg} kg/kg at 293.15 K, 101325 Pa -> RH={rh_computed:.1f}%")

print("\n" + "=" * 60)
print("  Example complete. See ki_tools_common/ for full API.")
print("=" * 60)
