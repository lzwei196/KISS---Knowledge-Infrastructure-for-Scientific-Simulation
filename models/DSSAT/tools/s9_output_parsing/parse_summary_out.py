#!/usr/bin/env python3
"""
parse_summary_out.py - Parses DSSAT Summary.OUT file into structured data.

The Summary.OUT file is the primary DSSAT output containing one row per
treatment/season with key simulated results (yield, phenology dates,
water balance, nitrogen balance, etc.).

Format:
    Line 1: *SUMMARY header with model version info
    Line 2: blank
    Line 3: ! column group descriptions
    Line 4: @ column headers (space-delimited fixed-width)
    Line 5+: data records (one per run/treatment)

Key variables parsed:
    HWAH  - Harvested yield, kg/ha at harvest maturity
    ADAT  - Anthesis date (YYDDD)
    MDAT  - Maturity date (YYDDD)
    PDAT  - Planting date (YYDDD)
    ETCM  - Cumulative ET, mm
    PRCM  - Cumulative precipitation, mm
    NUCM  - Cumulative N uptake, kg/ha
    NICM  - Cumulative N applied, kg/ha

Exit codes:
    0 = success
    1 = input error
    2 = processing error
    3 = output error
"""

import sys
import os
import logging
import json
import math
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# INPUT VARIABLES (agent sets these before invocation)
# ---------------------------------------------------------------------------
SUMMARY_FILE_PATH = ""      # Path to Summary.OUT file (required)
OUTPUT_FORMAT = "dict"      # "dict" for list of dicts, "dataframe" for pandas DataFrame
OUTPUT_JSON = True          # If True, print JSON result to stdout
SANITY_CHECKS = True        # If True, run sanity checks on parsed values

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger("parse_summary_out")

# ---------------------------------------------------------------------------
# DSSAT date columns (in YYDDD format that need conversion)
# ---------------------------------------------------------------------------
DATE_COLUMNS = {"SDAT", "PDAT", "EDAT", "ADAT", "MDAT", "HDAT"}

# Numeric columns that should be parsed as integers
INTEGER_COLUMNS = {
    "RUNNO", "TRNO", "WYEAR", "HYEAR", "DWAP", "CWAM", "HWAM", "HWAH",
    "BWAH", "PWAM", "IR#M", "IRCM", "PRCM", "ETCM", "EPCM", "ESCM",
    "ROCM", "DRCM", "SWXM", "NI#M", "NICM", "NUCM", "NLCM", "NIAM",
    "NMINC", "CNAM", "GNAM", "PI#M", "PICM", "KI#M", "KICM",
    "RECM", "ONTAM", "ONAM", "OPTAM", "OPAM", "OCTAM", "OCAM",
    "NDCH", "PRCP", "H#AM",
}

# Float columns
FLOAT_COLUMNS = {
    "XLAT", "LONG", "ELEV", "HWUM", "H#UM", "HIAM", "LAIX",
    "NFXM", "SLNF", "N2OEM", "CO2EM", "CH4EM",
    "DMPPM", "DMPEM", "DMPTM", "DMPIM",
    "YPPM", "YPEM", "YPTM", "YPIM",
    "DPNAM", "DPNUM", "YPNAM", "YPNUM",
    "TMAXA", "TMINA", "SRADA", "DAYLA", "CO2A",
    "ETCP", "ESCP", "EPCP",
    "PUPC", "SPAM", "KUPC", "SKAM",
    "EYLDH",
}


def yyddd_to_iso(yyddd_val):
    """Convert DSSAT YYDDD or YYYYDDD integer to ISO date string (YYYY-MM-DD).

    DSSAT Y2K convention:
        YY 0-70  -> 2000-2070
        YY 71-99 -> 1971-1999
        YYYY (7-digit) -> used directly

    Args:
        yyddd_val: Integer date value (e.g., 82133 or 1982133).

    Returns:
        str in YYYY-MM-DD format, or None if invalid/missing.
    """
    if yyddd_val is None or yyddd_val == -99:
        return None

    try:
        val = int(yyddd_val)
    except (ValueError, TypeError):
        return None

    if val <= 0:
        return None

    s = str(val)
    if len(s) <= 5:
        yy = val // 1000
        ddd = val % 1000
        if yy <= 70:
            year = 2000 + yy
        else:
            year = 1900 + yy
    elif len(s) <= 7:
        year = val // 1000
        ddd = val % 1000
    else:
        return None

    if ddd < 1 or ddd > 366:
        return None

    try:
        date_obj = datetime(year, 1, 1) + timedelta(days=ddd - 1)
        return date_obj.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return None


def parse_value(val_str, col_name):
    """Parse a single value string based on column name/type.

    Args:
        val_str: Raw string value from the file.
        col_name: Column header name.

    Returns:
        Parsed value (int, float, str, or None for missing).
    """
    s = val_str.strip()

    # Check for missing value
    if s == "-99" or s == "-99.0" or s == "-99." or s == "-99.000":
        return None

    try:
        fval = float(s)
        if fval == -99.0:
            return None
        if math.isnan(fval) or math.isinf(fval):
            return None
    except ValueError:
        # Non-numeric value (e.g., model name, experiment name)
        return s

    # Date columns: keep as integer for later conversion
    if col_name in DATE_COLUMNS:
        try:
            return int(fval)
        except (ValueError, OverflowError):
            return None

    # Integer columns
    if col_name in INTEGER_COLUMNS:
        try:
            return int(round(fval))
        except (ValueError, OverflowError):
            return fval

    # Float columns
    if col_name in FLOAT_COLUMNS:
        return fval

    # Default: try int, then float, then string
    if fval == int(fval) and abs(fval) < 1e15:
        return int(fval)
    return fval


def parse_summary_file(filepath):
    """Parse a DSSAT Summary.OUT file into a list of record dicts.

    Args:
        filepath: Path to Summary.OUT file.

    Returns:
        tuple of (records_list, column_names, warnings_list)
        where each record is an OrderedDict.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    warnings = []
    column_names = []
    records = []

    # Find the @ header line
    header_line_idx = None
    for i, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped.startswith("@"):
            header_line_idx = i
            break

    if header_line_idx is None:
        raise ValueError("Cannot find column header line (starting with @) in Summary.OUT.")

    # Parse column headers
    # The Summary.OUT uses fixed-width columns, but the header starts with @
    header_raw = raw_lines[header_line_idx]

    # The header line has columns separated by whitespace
    # We need to determine column positions from the header
    header_stripped = header_raw.rstrip("\n").rstrip("\r")

    # Strategy: find each column header's start position in the header line
    # Split on whitespace to get column names
    col_parts = header_stripped.split()
    # Remove @ from first column
    if col_parts[0].startswith("@"):
        col_parts[0] = col_parts[0].lstrip("@").strip()
        if not col_parts[0]:
            col_parts = col_parts[1:]

    column_names = col_parts

    # Build column position map using header string positions
    col_positions = []  # list of (start, end, name)
    search_start = 0
    for col in column_names:
        pos = header_stripped.find(col, search_start)
        if pos >= 0:
            col_positions.append((pos, col))
            search_start = pos + len(col)
        else:
            # Column name not found at expected position; fall back
            col_positions.append((search_start, col))
            search_start += len(col) + 1

    # Determine column boundaries (start, end) for each column
    col_bounds = []
    for k in range(len(col_positions)):
        start = col_positions[k][0]
        if k + 1 < len(col_positions):
            end = col_positions[k + 1][0]
        else:
            end = None  # Last column extends to end of line
        col_bounds.append((start, end, col_positions[k][1]))

    # Parse data records
    for i in range(header_line_idx + 1, len(raw_lines)):
        line = raw_lines[i]
        stripped = line.strip()

        # Skip empty lines, comments, and header lines
        if not stripped:
            continue
        if stripped.startswith("*") or stripped.startswith("!") or stripped.startswith("@"):
            continue

        # Parse using fixed-width column positions
        record = {}
        raw_line = line.rstrip("\n").rstrip("\r")

        for start, end, col_name in col_bounds:
            if start < len(raw_line):
                if end is not None and end <= len(raw_line):
                    val_str = raw_line[start:end]
                elif end is not None:
                    val_str = raw_line[start:]
                else:
                    val_str = raw_line[start:]

                val_str = val_str.strip()
                if val_str:
                    record[col_name] = parse_value(val_str, col_name)
                else:
                    record[col_name] = None
            else:
                record[col_name] = None

        # Only add if record has at least some data
        if any(v is not None for v in record.values()):
            records.append(record)

    return records, column_names, warnings


def convert_dates(records):
    """Convert YYDDD date columns to YYYY-MM-DD format in place.

    Adds new columns with '_ISO' suffix for each date column.

    Args:
        records: List of record dicts (modified in place).

    Returns:
        List of date columns that were converted.
    """
    converted = []
    for col in DATE_COLUMNS:
        iso_col = col + "_ISO"
        any_converted = False
        for rec in records:
            if col in rec and rec[col] is not None:
                iso_date = yyddd_to_iso(rec[col])
                rec[iso_col] = iso_date
                any_converted = True
            else:
                rec[iso_col] = None
        if any_converted:
            converted.append(col)

    return converted


def run_sanity_checks(records):
    """Run sanity checks on parsed Summary.OUT records.

    Checks:
        - HWAH in [0, 25000] kg/ha (extreme upper bound)
        - PDAT < ADAT < MDAT (phenological sequence)

    Args:
        records: List of record dicts.

    Returns:
        list of warning strings.
    """
    warnings = []

    for idx, rec in enumerate(records):
        run_id = rec.get("RUNNO", idx + 1)
        trt_id = rec.get("TRNO", "?")

        # HWAH range check
        hwah = rec.get("HWAH")
        if hwah is not None:
            if hwah < 0:
                warnings.append(
                    f"Run {run_id}, Trt {trt_id}: HWAH = {hwah} < 0 kg/ha "
                    f"(negative yield indicates simulation failure)."
                )
            elif hwah > 25000:
                warnings.append(
                    f"Run {run_id}, Trt {trt_id}: HWAH = {hwah} > 25000 kg/ha "
                    f"(unusually high yield, verify simulation)."
                )

        # Phenological date sequence: PDAT < ADAT < MDAT
        pdat = rec.get("PDAT")
        adat = rec.get("ADAT")
        mdat = rec.get("MDAT")

        if pdat is not None and adat is not None:
            if adat <= pdat:
                warnings.append(
                    f"Run {run_id}, Trt {trt_id}: ADAT ({adat}) <= PDAT ({pdat}). "
                    f"Anthesis should occur after planting."
                )
        if adat is not None and mdat is not None:
            if mdat <= adat:
                warnings.append(
                    f"Run {run_id}, Trt {trt_id}: MDAT ({mdat}) <= ADAT ({adat}). "
                    f"Maturity should occur after anthesis."
                )
        if pdat is not None and mdat is not None:
            if mdat <= pdat:
                warnings.append(
                    f"Run {run_id}, Trt {trt_id}: MDAT ({mdat}) <= PDAT ({pdat}). "
                    f"Maturity should occur after planting."
                )

        # ETCM should be positive
        etcm = rec.get("ETCM")
        if etcm is not None and etcm < 0:
            warnings.append(
                f"Run {run_id}, Trt {trt_id}: ETCM = {etcm} < 0 mm "
                f"(negative evapotranspiration)."
            )

        # PRCM should be non-negative
        prcm = rec.get("PRCM")
        if prcm is not None and prcm < 0:
            warnings.append(
                f"Run {run_id}, Trt {trt_id}: PRCM = {prcm} < 0 mm "
                f"(negative precipitation)."
            )

    return warnings


def main():
    """Entry point: parse Summary.OUT and output structured data."""
    # -----------------------------------------------------------------------
    # PRECONDITIONS
    # -----------------------------------------------------------------------
    if not SUMMARY_FILE_PATH:
        logger.error("SUMMARY_FILE_PATH must be set before running.")
        sys.exit(1)

    if not os.path.isfile(SUMMARY_FILE_PATH):
        logger.error("Summary file not found: %s", SUMMARY_FILE_PATH)
        sys.exit(1)

    if OUTPUT_FORMAT not in ("dict", "dataframe"):
        logger.error("OUTPUT_FORMAT must be 'dict' or 'dataframe', got '%s'", OUTPUT_FORMAT)
        sys.exit(1)

    # -----------------------------------------------------------------------
    # CORE PROCESSING
    # -----------------------------------------------------------------------
    try:
        records, column_names, parse_warnings = parse_summary_file(SUMMARY_FILE_PATH)
    except ValueError as e:
        logger.error("Parsing error: %s", e)
        sys.exit(2)
    except Exception as e:
        logger.error("Unexpected parsing error: %s", e, exc_info=True)
        sys.exit(2)

    if not records:
        logger.error("No data records found in Summary.OUT file.")
        sys.exit(2)

    logger.info("Parsed %d records with %d columns.", len(records), len(column_names))

    # Convert dates
    converted_dates = convert_dates(records)
    if converted_dates:
        logger.info("Converted date columns: %s", ", ".join(converted_dates))

    # Sanity checks
    sanity_warnings = []
    if SANITY_CHECKS:
        sanity_warnings = run_sanity_checks(records)
        if sanity_warnings:
            for w in sanity_warnings:
                logger.warning(w)

    all_warnings = parse_warnings + sanity_warnings

    # -----------------------------------------------------------------------
    # POSTCONDITIONS
    # -----------------------------------------------------------------------
    if not isinstance(records, list):
        logger.error("records must be a list, got %s", type(records))
        sys.exit(3)

    if len(records) == 0:
        logger.error("No records after parsing (postcondition failure).")
        sys.exit(3)

    # Verify each record has the expected columns
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            logger.error("Record %d is not a dict, got %s", i, type(rec))
            sys.exit(3)

    # -----------------------------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------------------------
    if OUTPUT_FORMAT == "dataframe":
        try:
            import pandas as pd
            df = pd.DataFrame(records)
            logger.info("Created DataFrame with shape %s", df.shape)
            if OUTPUT_JSON:
                print(df.to_json(orient="records", indent=2))
            # The DataFrame is available as the result
        except ImportError:
            logger.warning(
                "pandas not available. Falling back to dict output."
            )
            OUTPUT_FORMAT_ACTUAL = "dict"
            if OUTPUT_JSON:
                output = {
                    "records": records,
                    "column_names": column_names,
                    "record_count": len(records),
                    "warnings": all_warnings,
                }
                print(json.dumps(output, indent=2, default=str))
    else:
        if OUTPUT_JSON:
            output = {
                "records": records,
                "column_names": column_names,
                "record_count": len(records),
                "warnings": all_warnings,
            }
            print(json.dumps(output, indent=2, default=str))

    logger.info("Successfully parsed %d records.", len(records))
    sys.exit(0)


if __name__ == "__main__":
    main()
