#!/usr/bin/env python3
"""
calculate_tav_amp.py - Calculates TAV and AMP from DSSAT weather data.

TAV = Mean Annual Temperature = mean of all daily (TMAX + TMIN) / 2
AMP = Annual Temperature Amplitude = (max monthly mean - min monthly mean) / 2
    where monthly mean = average of daily (TMAX + TMIN) / 2 for each calendar month,
    averaged across all years of data.

These values are required in the .WTH file header for DSSAT soil temperature
initialization (STEMP subroutine).

Input: path to .WTH file OR parallel arrays of TMAX, TMIN, dates.
Output: TAV and AMP values; optionally updates the .WTH file header.

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
from collections import defaultdict

# ---------------------------------------------------------------------------
# INPUT VARIABLES (agent sets these before invocation)
# ---------------------------------------------------------------------------
WEATHER_FILE_PATH = ""      # Path to .WTH file (optional if arrays provided)
TMAX_ARRAY = None           # List of float TMAX values (optional)
TMIN_ARRAY = None           # List of float TMIN values (optional)
DATE_ARRAY = None           # List of date strings in YYDDD or YYYY-MM-DD format (optional)
UPDATE_FILE = False         # If True, update TAV and AMP in the .WTH header
OUTPUT_JSON = True          # If True, print JSON result to stdout
MIN_DAYS = 365              # Minimum days of data required for reliable calculation

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger("calculate_tav_amp")


def yyddd_to_date(yyddd_str):
    """Convert YYDDD or YYYYDDD string to a datetime.date object.

    DSSAT Y2K convention:
        YY 0-70  -> 2000-2070
        YY 71-99 -> 1971-1999

    Args:
        yyddd_str: String like '82001' or '1982001'.

    Returns:
        datetime.date or None if unparseable.
    """
    s = yyddd_str.strip()
    try:
        val = int(s)
    except ValueError:
        return None

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
        return datetime(year, 1, 1).date() + timedelta(days=ddd - 1)
    except (ValueError, OverflowError):
        return None


def parse_date_flexible(date_str):
    """Parse a date string in YYDDD, YYYYDDD, or YYYY-MM-DD format.

    Args:
        date_str: Date string.

    Returns:
        datetime.date or None.
    """
    s = date_str.strip()

    # Try YYYY-MM-DD format
    if "-" in s:
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None

    # Try YYDDD / YYYYDDD
    return yyddd_to_date(s)


def parse_wth_file(filepath):
    """Parse a DSSAT .WTH file and extract TMAX, TMIN, and dates.

    Args:
        filepath: Path to the .WTH file.

    Returns:
        tuple of (dates_list, tmax_list, tmin_list, header_line_index, station_data_line_index, raw_lines)
        where header_line_index is the line index of the @INSI header,
        and station_data_line_index is the line index of the station data.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    # Find station header
    station_header_idx = None
    station_data_idx = None
    daily_header_idx = None

    for i, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped.startswith("@") and "INSI" in stripped:
            station_header_idx = i
            for j in range(i + 1, len(raw_lines)):
                sj = raw_lines[j].strip()
                if sj and not sj.startswith("!") and not sj.startswith("@"):
                    station_data_idx = j
                    break
        if stripped.startswith("@DATE"):
            daily_header_idx = i

    if daily_header_idx is None:
        raise ValueError("Cannot find @DATE header line in weather file.")

    # Parse daily header columns
    header_line = raw_lines[daily_header_idx].strip().lstrip("@")
    daily_cols = header_line.split()

    # Find column indices
    try:
        date_col = daily_cols.index("DATE")
    except ValueError:
        date_col = 0
    try:
        tmax_col = daily_cols.index("TMAX")
    except ValueError:
        raise ValueError("TMAX column not found in daily data header.")
    try:
        tmin_col = daily_cols.index("TMIN")
    except ValueError:
        raise ValueError("TMIN column not found in daily data header.")

    dates_list = []
    tmax_list = []
    tmin_list = []

    for i in range(daily_header_idx + 1, len(raw_lines)):
        stripped = raw_lines[i].strip()
        if not stripped or stripped.startswith("!") or stripped.startswith("*") or stripped.startswith("@"):
            continue

        parts = stripped.split()
        if len(parts) <= max(date_col, tmax_col, tmin_col):
            continue

        d = yyddd_to_date(parts[date_col])
        if d is None:
            continue

        try:
            tmax_val = float(parts[tmax_col])
            tmin_val = float(parts[tmin_col])
        except (ValueError, IndexError):
            continue

        # Skip missing values
        if tmax_val == -99 or tmin_val == -99:
            continue
        if math.isnan(tmax_val) or math.isnan(tmin_val):
            continue

        dates_list.append(d)
        tmax_list.append(tmax_val)
        tmin_list.append(tmin_val)

    return dates_list, tmax_list, tmin_list, station_header_idx, station_data_idx, raw_lines


def calculate_tav_amp(dates, tmax_vals, tmin_vals):
    """Calculate TAV and AMP from daily temperature data.

    TAV = mean of all daily Tavg where Tavg = (TMAX + TMIN) / 2
    AMP = (max monthly mean Tavg - min monthly mean Tavg) / 2
        Monthly means are first computed per year-month, then averaged
        across years for each calendar month (1-12), producing 12 values.
        AMP uses the range of those 12 averaged monthly means.

    Args:
        dates: List of datetime.date objects.
        tmax_vals: List of float TMAX values (degC).
        tmin_vals: List of float TMIN values (degC).

    Returns:
        dict with keys: TAV, AMP, n_days, n_years, monthly_means (list of 12).
    """
    n = len(dates)
    if n == 0:
        raise ValueError("No valid temperature data available.")

    # Compute daily average temperatures
    tavg_daily = [(tmax_vals[i] + tmin_vals[i]) / 2.0 for i in range(n)]

    # TAV: simple mean of all daily averages
    tav = sum(tavg_daily) / n

    # Monthly means: group by (year, month), then average across years per month
    # Step 1: accumulate sums and counts per (year, month)
    year_month_sums = defaultdict(float)
    year_month_counts = defaultdict(int)

    for i in range(n):
        key = (dates[i].year, dates[i].month)
        year_month_sums[key] += tavg_daily[i]
        year_month_counts[key] += 1

    # Step 2: compute mean for each (year, month)
    year_month_means = {}
    for key in year_month_sums:
        year_month_means[key] = year_month_sums[key] / year_month_counts[key]

    # Step 3: average across years for each calendar month
    month_sums = defaultdict(float)
    month_counts = defaultdict(int)
    for (yr, mo), mean_val in year_month_means.items():
        month_sums[mo] += mean_val
        month_counts[mo] += 1

    monthly_means = {}
    for mo in range(1, 13):
        if month_counts[mo] > 0:
            monthly_means[mo] = month_sums[mo] / month_counts[mo]

    if len(monthly_means) == 0:
        raise ValueError("No complete months of data available.")

    # AMP = (max_monthly_mean - min_monthly_mean) / 2
    max_monthly = max(monthly_means.values())
    min_monthly = min(monthly_means.values())
    amp = (max_monthly - min_monthly) / 2.0

    # Collect year set
    years = sorted(set(d.year for d in dates))

    # Build monthly means list (12 values, None for missing months)
    monthly_means_list = [
        round(monthly_means.get(m, None), 2) if monthly_means.get(m) is not None else None
        for m in range(1, 13)
    ]

    return {
        "TAV": round(tav, 1),
        "AMP": round(amp, 1),
        "n_days": n,
        "n_years": len(years),
        "years": years,
        "n_months_with_data": len(monthly_means),
        "monthly_means": monthly_means_list,
    }


def update_wth_header(filepath, tav, amp, station_header_idx, station_data_idx, raw_lines):
    """Update TAV and AMP values in the .WTH file header.

    This modifies the station data line in place, preserving column alignment.

    Args:
        filepath: Path to the .WTH file.
        tav: New TAV value.
        amp: New AMP value.
        station_header_idx: Line index of the @INSI header.
        station_data_idx: Line index of the station data.
        raw_lines: List of all lines in the file.

    Returns:
        bool: True if successful.
    """
    if station_header_idx is None or station_data_idx is None:
        raise ValueError("Cannot locate station header/data lines for update.")

    header_line = raw_lines[station_header_idx]
    data_line = raw_lines[station_data_idx]

    # Parse header to find TAV and AMP column positions
    # Use the header line character positions to find column boundaries
    header_stripped = header_line.rstrip("\n").rstrip("\r")

    # Find column positions from the header line
    cols = header_stripped.split()
    # Remove leading @ from first column
    if cols[0].startswith("@"):
        cols[0] = cols[0].lstrip("@").strip()

    # Find TAV and AMP positions in the header line
    tav_pos = header_stripped.upper().find("TAV")
    amp_pos = header_stripped.upper().find("AMP")

    if tav_pos < 0 or amp_pos < 0:
        raise ValueError("Cannot find TAV or AMP columns in header.")

    # Parse the data line into tokens using the same column positions
    data_parts = data_line.split()
    header_parts = header_stripped.lstrip("@ ").split()

    # Find indices of TAV and AMP in the header columns
    tav_idx = None
    amp_idx = None
    for i, col in enumerate(header_parts):
        if col.upper() == "TAV":
            tav_idx = i
        if col.upper() == "AMP":
            amp_idx = i

    if tav_idx is None or amp_idx is None:
        raise ValueError("Cannot find TAV or AMP column index.")

    # Replace values in data parts
    if tav_idx < len(data_parts):
        data_parts[tav_idx] = f"{tav:5.1f}"
    if amp_idx < len(data_parts):
        data_parts[amp_idx] = f"{amp:5.1f}"

    # Reconstruct the data line preserving DSSAT column alignment
    # The DSSAT format expects fixed-width columns matching the header
    # Standard format: @_INSI______LAT_____LONG__ELEV___TAV___AMP_REFHT_WNDHT
    #                    XXXX__##.###_##.###__####__##.#__##.#__#.##__#.##
    # We rebuild using the header column positions for alignment
    new_data_line = "  {:<4s} {:>8s} {:>8s} {:>5s} {:>5s} {:>5s} {:>5s} {:>5s}\n".format(
        data_parts[0] if len(data_parts) > 0 else "",
        data_parts[1] if len(data_parts) > 1 else "",
        data_parts[2] if len(data_parts) > 2 else "",
        data_parts[3] if len(data_parts) > 3 else "",
        data_parts[tav_idx].strip() if tav_idx < len(data_parts) else "",
        data_parts[amp_idx].strip() if amp_idx < len(data_parts) else "",
        data_parts[6] if len(data_parts) > 6 else "",
        data_parts[7] if len(data_parts) > 7 else "",
    )

    raw_lines[station_data_idx] = new_data_line

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(raw_lines)

    return True


def main():
    """Entry point: calculate TAV and AMP."""
    # -----------------------------------------------------------------------
    # PRECONDITIONS
    # -----------------------------------------------------------------------
    use_file = bool(WEATHER_FILE_PATH)
    use_arrays = (TMAX_ARRAY is not None and TMIN_ARRAY is not None
                  and DATE_ARRAY is not None)

    if not use_file and not use_arrays:
        logger.error(
            "Must provide either WEATHER_FILE_PATH or "
            "(TMAX_ARRAY, TMIN_ARRAY, DATE_ARRAY)."
        )
        sys.exit(1)

    if use_arrays:
        if len(TMAX_ARRAY) != len(TMIN_ARRAY):
            logger.error(
                "TMAX_ARRAY length (%d) != TMIN_ARRAY length (%d).",
                len(TMAX_ARRAY), len(TMIN_ARRAY)
            )
            sys.exit(1)
        if len(TMAX_ARRAY) != len(DATE_ARRAY):
            logger.error(
                "TMAX_ARRAY length (%d) != DATE_ARRAY length (%d).",
                len(TMAX_ARRAY), len(DATE_ARRAY)
            )
            sys.exit(1)

    if use_file and not os.path.isfile(WEATHER_FILE_PATH):
        logger.error("Weather file not found: %s", WEATHER_FILE_PATH)
        sys.exit(1)

    # -----------------------------------------------------------------------
    # CORE PROCESSING
    # -----------------------------------------------------------------------
    station_header_idx = None
    station_data_idx = None
    raw_lines = None

    try:
        if use_file:
            dates, tmax_vals, tmin_vals, station_header_idx, station_data_idx, raw_lines = \
                parse_wth_file(WEATHER_FILE_PATH)
        else:
            # Parse dates from array
            dates = []
            tmax_vals = []
            tmin_vals = []
            for i, date_str in enumerate(DATE_ARRAY):
                d = parse_date_flexible(str(date_str))
                if d is None:
                    logger.warning("Skipping unparseable date at index %d: '%s'", i, date_str)
                    continue
                tx = float(TMAX_ARRAY[i])
                tn = float(TMIN_ARRAY[i])
                if tx == -99 or tn == -99 or math.isnan(tx) or math.isnan(tn):
                    continue
                dates.append(d)
                tmax_vals.append(tx)
                tmin_vals.append(tn)

        if len(dates) < MIN_DAYS:
            logger.warning(
                "Only %d days of valid data (minimum recommended: %d). "
                "Results may not be representative.",
                len(dates), MIN_DAYS
            )

        result = calculate_tav_amp(dates, tmax_vals, tmin_vals)

    except ValueError as e:
        logger.error("Processing error: %s", e)
        sys.exit(2)
    except Exception as e:
        logger.error("Unexpected processing error: %s", e, exc_info=True)
        sys.exit(2)

    # -----------------------------------------------------------------------
    # POSTCONDITIONS
    # -----------------------------------------------------------------------
    if result["TAV"] is None or result["AMP"] is None:
        logger.error("TAV or AMP calculation returned None.")
        sys.exit(3)

    if math.isnan(result["TAV"]) or math.isnan(result["AMP"]):
        logger.error("TAV or AMP is NaN.")
        sys.exit(3)

    # Sanity checks on computed values
    if result["TAV"] < -50 or result["TAV"] > 50:
        logger.warning(
            "TAV = %.1f seems extreme. Verify input data.", result["TAV"]
        )

    if result["AMP"] < 0 or result["AMP"] > 30:
        logger.warning(
            "AMP = %.1f seems extreme. Verify input data.", result["AMP"]
        )

    # -----------------------------------------------------------------------
    # OPTIONAL FILE UPDATE
    # -----------------------------------------------------------------------
    if UPDATE_FILE and use_file:
        try:
            update_wth_header(
                WEATHER_FILE_PATH, result["TAV"], result["AMP"],
                station_header_idx, station_data_idx, raw_lines
            )
            logger.info(
                "Updated %s: TAV=%.1f, AMP=%.1f",
                WEATHER_FILE_PATH, result["TAV"], result["AMP"]
            )
            result["file_updated"] = True
        except Exception as e:
            logger.error("Failed to update file: %s", e)
            result["file_updated"] = False
    else:
        result["file_updated"] = False

    # -----------------------------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------------------------
    logger.info("TAV = %.1f degC, AMP = %.1f degC", result["TAV"], result["AMP"])
    logger.info(
        "Based on %d days of data across %d year(s).",
        result["n_days"], result["n_years"]
    )

    if OUTPUT_JSON:
        print(json.dumps(result, indent=2, default=str))

    sys.exit(0)


if __name__ == "__main__":
    main()
