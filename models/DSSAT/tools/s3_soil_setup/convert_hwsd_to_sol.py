#!/usr/bin/env python3
"""
convert_hwsd_to_sol.py — Convert HWSD soil data to DSSAT SOIL.SOL format.

Reads HWSD raster + CSV database to extract soil properties for a location,
then generates a DSSAT-compatible SOIL.SOL file with 2 layers.

Usage:
    python convert_hwsd_to_sol.py \
        --lat 32.43 --lon 115.60 \
        --output SOIL.SOL \
        --soil_id WJBA000001
"""

import argparse
import os
import sys
import math
import numpy as np
import pandas as pd
from pathlib import Path

HYDROCRAFT = "/mnt/disk1/Hydrocraft_server"
HWSD_RASTER = os.path.join(HYDROCRAFT, "data/soil/HWSD_RASTER/hwsd.bil")
HWSD_CSV = os.path.join(HYDROCRAFT, "data/soil/HWSD_DATA.csv")


def classify_texture(sand, silt, clay):
    """USDA texture classification from sand/silt/clay percentages."""
    if sand >= 85:
        return "Sa"
    elif sand >= 70 and clay < 15:
        return "LoSa"
    elif clay >= 40:
        return "C"
    elif clay >= 27:
        if sand >= 20:
            return "SaCl"
        elif silt >= 40:
            return "SiCl"
        else:
            return "ClLo"
    elif silt >= 50:
        if clay >= 12:
            return "SiLo"
        else:
            return "Si"
    elif sand >= 52:
        return "SaLo"
    else:
        return "Lo"


def saxton_rawls(sand, clay, om=1.5):
    """Saxton-Rawls pedotransfer for DSSAT soil hydraulic properties."""
    s, c = sand / 100.0, clay / 100.0
    om_frac = om / 100.0

    # Wilting point (1500 kPa)
    wp = -0.024 * s + 0.487 * c + 0.006 * om_frac + 0.005 * s * om_frac - 0.013 * c * om_frac + 0.068 * s * c + 0.031
    wp = max(0.01, wp)

    # Field capacity (33 kPa)
    fc = wp + 0.2576 - 0.02 * s + 0.036 * c + 0.0299 * om_frac
    fc = max(wp + 0.01, fc)

    # Saturation
    sat = 0.332 - 7.251e-4 * sand + 0.01276 * math.log10(max(clay, 0.1))
    sat = max(fc + 0.01, min(0.60, sat + 0.40))

    # Saturated hydraulic conductivity (cm/hr)
    ksat = max(0.01, 1930 * (sat - fc) ** (3 - 1.0 / (2.0 * max(0.1, clay / 100.0))))

    # Bulk density
    bd = max(0.9, min(1.8, 2.65 * (1 - sat)))

    return {
        'SLLL': round(wp, 3),      # lower limit (wilting point)
        'SDUL': round(fc, 3),      # drained upper limit (field capacity)
        'SSAT': round(sat, 3),     # saturated water content
        'SSKS': round(ksat, 2),    # sat hydraulic conductivity cm/hr
        'SBDM': round(bd, 2),      # bulk density g/cm3
    }


def lookup_hwsd(lat, lon):
    """Look up HWSD soil properties for a location."""
    # Read raster to get MU_GLOBAL
    mu_id = None
    try:
        import rasterio
        with rasterio.open(HWSD_RASTER) as src:
            row, col = src.index(lon, lat)
            mu_id = int(src.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0])
    except Exception as e:
        print(f"  WARNING: HWSD raster lookup failed: {e}")

    # Fallback: try CSV
    if mu_id and os.path.exists(HWSD_CSV):
        df = pd.read_csv(HWSD_CSV, low_memory=False)
        row = df[df['MU_GLOBAL'] == mu_id]
        if len(row) > 0:
            r = row.iloc[0]
            return {
                'mu_id': mu_id,
                'T_SAND': float(r.get('T_SAND', 40)),
                'T_SILT': float(r.get('T_SILT', 40)),
                'T_CLAY': float(r.get('T_CLAY', 20)),
                'T_OC': float(r.get('T_OC', 1.5)),
                'T_PH_H2O': float(r.get('T_PH_H2O', 6.5)),
                'T_REF_BULK_DENSITY': float(r.get('T_REF_BULK_DENSITY', 1.3)),
                'S_SAND': float(r.get('S_SAND', r.get('T_SAND', 40))),
                'S_SILT': float(r.get('S_SILT', r.get('T_SILT', 40))),
                'S_CLAY': float(r.get('S_CLAY', r.get('T_CLAY', 20))),
            }

    # Default if lookup fails
    print(f"  WARNING: Using default soil (loam) for ({lat}, {lon})")
    return {'mu_id': 0, 'T_SAND': 40, 'T_SILT': 40, 'T_CLAY': 20, 'T_OC': 1.5,
            'T_PH_H2O': 6.5, 'T_REF_BULK_DENSITY': 1.3,
            'S_SAND': 40, 'S_SILT': 40, 'S_CLAY': 20}


def write_sol(soil_props, output_path, soil_id, lat, lon):
    """Write DSSAT SOIL.SOL file."""
    top_sand = soil_props['T_SAND']
    top_silt = soil_props['T_SILT']
    top_clay = soil_props['T_CLAY']
    sub_sand = soil_props.get('S_SAND', top_sand)
    sub_silt = soil_props.get('S_SILT', top_silt)
    sub_clay = soil_props.get('S_CLAY', top_clay)

    tex_top = classify_texture(top_sand, top_silt, top_clay)
    tex_sub = classify_texture(sub_sand, sub_silt, sub_clay)
    hyd_top = saxton_rawls(top_sand, top_clay, soil_props.get('T_OC', 1.5))
    hyd_sub = saxton_rawls(sub_sand, sub_clay, soil_props.get('T_OC', 0.5))

    ph = soil_props.get('T_PH_H2O', 6.5)

    with open(output_path, 'w') as f:
        f.write("*SOILS: HWSD-derived soil profile\n\n")
        f.write(f"*{soil_id}  HWSD   {tex_top:5s}    {200:5d}  HWSD MU={soil_props['mu_id']}\n")
        f.write(f"@SITE        COUNTRY          LAT     LONG SCS FAMILY\n")
        f.write(f" HWSD        GLOBAL       {lat:7.3f} {lon:8.3f} {tex_top}\n")
        f.write(f"@ SCOM  SALB  SLU1  SLDR  SLRO  SLNF  SLPF  SMHB  SMPX  SMKE\n")
        f.write(f"    BN  0.13   6.0  0.60  73.0  1.00  1.00 SA001 SA001 SA001\n")
        f.write(f"@  SLB  SLMH  SLLL  SDUL  SSAT  SRGF  SSKS  SBDM  SLOC  SLCL  SLSI  SLCF  SLNI  SLHW  SLHB  SCEC\n")
        # Top layer: 0-30 cm
        f.write(f"    30   Ap {hyd_top['SLLL']:5.3f} {hyd_top['SDUL']:5.3f} {hyd_top['SSAT']:5.3f}  1.00 {hyd_top['SSKS']:5.2f} {hyd_top['SBDM']:5.2f}  {soil_props.get('T_OC',1.5):4.2f} {top_clay:5.1f} {top_silt:5.1f}   0.0  0.10  {ph:4.1f}   -99   -99\n")
        # Subsoil: 30-200 cm
        f.write(f"   200   Bt {hyd_sub['SLLL']:5.3f} {hyd_sub['SDUL']:5.3f} {hyd_sub['SSAT']:5.3f}  0.20 {hyd_sub['SSKS']:5.2f} {hyd_sub['SBDM']:5.2f}  {soil_props.get('T_OC',1.5)*0.3:4.2f} {sub_clay:5.1f} {sub_silt:5.1f}   0.0  0.05  {ph:4.1f}   -99   -99\n")

    print(f"Written: {output_path}")
    print(f"  Soil ID: {soil_id}")
    print(f"  HWSD MU: {soil_props['mu_id']}")
    print(f"  Top: {tex_top} (sand={top_sand:.0f}% clay={top_clay:.0f}%)")
    print(f"  Sub: {tex_sub} (sand={sub_sand:.0f}% clay={sub_clay:.0f}%)")
    print(f"  Ksat top: {hyd_top['SSKS']:.2f} cm/hr, BD: {hyd_top['SBDM']:.2f} g/cm3")


def main():
    parser = argparse.ArgumentParser(description='Convert HWSD to DSSAT SOIL.SOL')
    parser.add_argument('--lat', type=float, required=True)
    parser.add_argument('--lon', type=float, required=True)
    parser.add_argument('--output', required=True, help='Output SOIL.SOL path')
    parser.add_argument('--soil_id', default='HWSD000001', help='DSSAT soil profile ID (10 chars)')
    args = parser.parse_args()

    print(f"Looking up HWSD soil for ({args.lat}, {args.lon})...")
    props = lookup_hwsd(args.lat, args.lon)
    write_sol(props, args.output, args.soil_id, args.lat, args.lon)


if __name__ == '__main__':
    main()
