#!/usr/bin/env python3
"""Preflight check for the real ESMF core and its ESMPy binding."""
import os, sys

PASS = FAIL = 0
MODEL_NAME = "ESMF"

def check_file(path, label, executable=False):
    global PASS, FAIL
    if os.path.isfile(path):
        if executable and not os.access(path, os.X_OK):
            print(f"  WARN  {label}: exists but not executable: {path}")
            FAIL += 1
        else:
            print(f"  OK    {label}: {path}")
            PASS += 1
    else:
        print(f"  FAIL  {label}: NOT FOUND at {path}")
        FAIL += 1

def check_dir(path, label):
    global PASS, FAIL
    if os.path.isdir(path):
        print(f"  OK    {label}: {path} ({len(os.listdir(path))} items)")
        PASS += 1
    else:
        print(f"  FAIL  {label}: NOT FOUND at {path}")
        FAIL += 1

def check_import(module, label):
    global PASS, FAIL
    try:
        __import__(module)
        print(f"  OK    {label}: import {module}")
        PASS += 1
    except ImportError as e:
        print(f"  FAIL  {label}: {e}")
        print(f"         Fix: pip install {module.split('.')[0]}")
        FAIL += 1

def check_core():
    """Initialise ESMF and exercise a native-backed Grid/Field operation."""
    global PASS, FAIL
    try:
        import numpy as np
        import esmpy
        esmpy.Manager(debug=False)
        grid = esmpy.Grid(max_index=np.array([2, 2], dtype=np.int32))
        field = esmpy.Field(grid, name="geoforge_preflight")
        field.data[...] = 7.0
        if field.data.shape != (2, 2) or float(field.data.sum()) != 28.0:
            raise RuntimeError("unexpected ESMF Field storage result")
        print(f"  OK    ESMF core: {esmpy.__version__} Grid/Field operation")
        PASS += 1
    except Exception as e:
        print(f"  FAIL  ESMF core initialisation: {type(e).__name__}: {e}")
        FAIL += 1

def main():
    global PASS, FAIL
    print(f"{' PREFLIGHT: ESMF ':=^60}")
    print()
    check_file(
        "KISSPATH_BINARIES/ESMF/env/Library/bin/ESMF_RegridWeightGen.exe",
        "ESMF_RegridWeightGen native executable",
        executable=True,
    )
    check_import("numpy", "NumPy")
    check_import("netCDF4", "netCDF4")
    check_import("esmpy", "esmpy")
    # A nested lookup forces importlib-based independent probes to execute
    # ESMPy's package initialiser instead of merely seeing its directory.
    check_import("esmpy.api.esmpymanager", "ESMPy native runtime binding")
    check_core()
    # Check diagnostics
    ki_dir = os.path.dirname(os.path.abspath(__file__))
    triplets = os.path.join(ki_dir, "diagnostics", "triplets.yaml")
    if os.path.isfile(triplets):
        print(f"  INFO  Diagnostics available: {triplets}")

    print(f"\n  Results: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL > 0 else 0)

if __name__ == "__main__":
    main()
