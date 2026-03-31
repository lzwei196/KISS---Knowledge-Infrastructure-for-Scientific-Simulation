"""
validation.py — Physical range validation and sanity checks for forcing and model output.

Consolidates range-checking logic duplicated across 30+ ki/tools/ scripts.

All functions are PURE — they inspect data and return diagnostics, but never
modify the data or produce file I/O.

Examples::

    >>> from ki_tools_common.validation import validate_forcing_ranges
    >>> warnings = validate_forcing_ranges({
    ...     'temperature': np.array([20.0, 25.0]),
    ...     'precipitation': np.array([0.0001, 0.0002]),
    ... })
    >>> for w in warnings:
    ...     print(w)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

Numeric = Union[float, int, np.ndarray]

# ---------------------------------------------------------------------------
# Physical bounds for common forcing variables.
# Each entry: (expected_unit, physical_min, physical_max,
#              unit_trap_condition, unit_trap_hint)
# ---------------------------------------------------------------------------
_FORCING_BOUNDS: Dict[str, dict] = {
    "temperature": {
        "expected_unit": "K",
        "phys_min": 180.0,
        "phys_max": 340.0,
        "traps": [
            {
                "condition": lambda mean: mean < 100.0,
                "hint": "Temperature likely in Celsius, expected Kelvin.",
            },
            {
                "condition": lambda mean: mean > 500.0,
                "hint": "Temperature may be in tenths of degrees or wrong variable.",
            },
        ],
    },
    "precipitation": {
        "expected_unit": "mm/day",
        "phys_min": 0.0,
        "phys_max": 1000.0,
        "traps": [
            {
                "condition": lambda mean: 0.0 < mean < 0.01,
                "hint": "Precipitation likely in kg/m2/s, expected mm/day. "
                "Multiply by 86400.",
            },
            {
                "condition": lambda mean: mean > 2000.0,
                "hint": "Precipitation may be in mm/year or wrong accumulation period.",
            },
        ],
    },
    "pressure": {
        "expected_unit": "Pa",
        "phys_min": 30000.0,
        "phys_max": 110000.0,
        "traps": [
            {
                "condition": lambda mean: 300.0 < mean < 1200.0,
                "hint": "Pressure likely in hPa, expected Pa. Multiply by 100.",
            },
            {
                "condition": lambda mean: 30.0 < mean < 120.0,
                "hint": "Pressure likely in kPa, expected Pa. Multiply by 1000.",
            },
        ],
    },
    "radiation": {
        "expected_unit": "W/m2",
        "phys_min": 0.0,
        "phys_max": 1400.0,
        "traps": [
            {
                "condition": lambda mean: mean > 2000.0,
                "hint": "Radiation may be in J/m2/day or MJ/m2/day, expected W/m2.",
            },
        ],
    },
    "wind": {
        "expected_unit": "m/s",
        "phys_min": 0.0,
        "phys_max": 120.0,
        "traps": [
            {
                "condition": lambda mean: mean > 200.0,
                "hint": "Wind likely in km/h or cm/s, expected m/s.",
            },
        ],
    },
    "humidity": {
        "expected_unit": "kg/kg",
        "phys_min": 0.0,
        "phys_max": 0.06,
        "traps": [
            {
                "condition": lambda mean: mean > 1.0,
                "hint": "Humidity likely in g/kg or percent, expected kg/kg.",
            },
        ],
    },
}


def validate_forcing_ranges(
    data_dict: Dict[str, np.ndarray],
) -> List[str]:
    """Check all forcing variables against physical bounds, with unit-trap hints.

    Args:
        data_dict: Mapping of variable name (e.g. ``'temperature'``,
            ``'precipitation'``) to 1-D or N-D numpy array of values.
            Variable names are matched case-insensitively and with common
            aliases (e.g. ``'temp'`` -> ``'temperature'``).

    Returns:
        List of human-readable warning strings. Empty list means all checks
        passed.

    Example::

        >>> ws = validate_forcing_ranges({'temperature': np.array([25.0, 30.0])})
        >>> any('likely in Celsius' in w for w in ws)
        True
    """
    # Alias mapping
    aliases = {
        "temp": "temperature",
        "tair": "temperature",
        "t2m": "temperature",
        "prec": "precipitation",
        "precip": "precipitation",
        "pre": "precipitation",
        "rainfall": "precipitation",
        "pres": "pressure",
        "press": "pressure",
        "sp": "pressure",
        "ps": "pressure",
        "srad": "radiation",
        "rsds": "radiation",
        "swdown": "radiation",
        "ssrd": "radiation",
        "wind": "wind",
        "u10": "wind",
        "wspd": "wind",
        "shum": "humidity",
        "q": "humidity",
        "huss": "humidity",
    }

    warnings_list: List[str] = []

    for var_name, data in data_dict.items():
        canonical = aliases.get(var_name.lower(), var_name.lower())
        if canonical not in _FORCING_BOUNDS:
            continue

        bounds = _FORCING_BOUNDS[canonical]
        arr = np.asarray(data, dtype=float)
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            warnings_list.append(
                f"[{var_name}] All values are NaN or infinite."
            )
            continue

        mean_val = float(np.nanmean(valid))
        min_val = float(np.nanmin(valid))
        max_val = float(np.nanmax(valid))

        # Physical range check
        if min_val < bounds["phys_min"]:
            warnings_list.append(
                f"[{var_name}] Minimum value {min_val:.4g} is below physical "
                f"lower bound {bounds['phys_min']} ({bounds['expected_unit']})."
            )
        if max_val > bounds["phys_max"]:
            warnings_list.append(
                f"[{var_name}] Maximum value {max_val:.4g} exceeds physical "
                f"upper bound {bounds['phys_max']} ({bounds['expected_unit']})."
            )

        # Unit-trap heuristics
        for trap in bounds.get("traps", []):
            try:
                if trap["condition"](mean_val):
                    warnings_list.append(
                        f"[{var_name}] UNIT TRAP: {trap['hint']} "
                        f"(mean={mean_val:.4g})"
                    )
            except Exception:
                pass

    return warnings_list


def validate_discharge(
    sim: np.ndarray,
    obs: np.ndarray,
) -> List[str]:
    """Validate simulated and observed discharge arrays before metric computation.

    Checks for NaN prevalence, negative values, and magnitude ratio.

    Args:
        sim: Simulated discharge array (e.g. m3/s).
        obs: Observed discharge array (e.g. m3/s).

    Returns:
        List of warning strings. Empty if no issues found.

    Example::

        >>> ws = validate_discharge(np.array([100, 200]), np.array([110, -5]))
        >>> any('negative' in w.lower() for w in ws)
        True
    """
    warnings_list: List[str] = []
    sim_arr = np.asarray(sim, dtype=float)
    obs_arr = np.asarray(obs, dtype=float)

    # Length mismatch
    if sim_arr.shape != obs_arr.shape:
        warnings_list.append(
            f"Shape mismatch: sim={sim_arr.shape}, obs={obs_arr.shape}."
        )

    # NaN prevalence
    sim_nan_pct = 100.0 * np.sum(np.isnan(sim_arr)) / max(sim_arr.size, 1)
    obs_nan_pct = 100.0 * np.sum(np.isnan(obs_arr)) / max(obs_arr.size, 1)

    if sim_nan_pct > 10.0:
        warnings_list.append(
            f"Simulated discharge has {sim_nan_pct:.1f}% NaN values."
        )
    if obs_nan_pct > 10.0:
        warnings_list.append(
            f"Observed discharge has {obs_nan_pct:.1f}% NaN values."
        )

    # Negative values
    if np.any(sim_arr[np.isfinite(sim_arr)] < 0):
        warnings_list.append(
            "Simulated discharge contains negative values."
        )
    if np.any(obs_arr[np.isfinite(obs_arr)] < 0):
        warnings_list.append(
            "Observed discharge contains negative values."
        )

    # Magnitude ratio
    sim_valid = sim_arr[np.isfinite(sim_arr)]
    obs_valid = obs_arr[np.isfinite(obs_arr)]

    if sim_valid.size > 0 and obs_valid.size > 0:
        sim_mean = np.mean(np.abs(sim_valid))
        obs_mean = np.mean(np.abs(obs_valid))
        if obs_mean > 0:
            ratio = sim_mean / obs_mean
            if ratio > 10.0 or ratio < 0.1:
                warnings_list.append(
                    f"Magnitude ratio sim/obs = {ratio:.2f}. "
                    f"Possible unit mismatch (sim_mean={sim_mean:.2f}, "
                    f"obs_mean={obs_mean:.2f})."
                )

    return warnings_list


def check_constant_values(
    data: np.ndarray,
    threshold: float = 1e-10,
) -> Dict[str, Any]:
    """Detect constant or fill-value-dominated arrays.

    Args:
        data: N-D numpy array to inspect.
        threshold: Standard deviation below which the data is considered
            constant.

    Returns:
        Dict with keys:
            - ``'is_constant'``: bool
            - ``'std'``: float — standard deviation of finite values
            - ``'fill_value_candidates'``: list of values that appear
              suspiciously often (> 50% of data)
            - ``'finite_fraction'``: float — fraction of finite values

    Example::

        >>> result = check_constant_values(np.array([1e20, 1e20, 1e20, 5.0]))
        >>> result['is_constant']
        False
        >>> len(result['fill_value_candidates']) > 0
        True
    """
    arr = np.asarray(data, dtype=float).ravel()
    finite_mask = np.isfinite(arr)
    finite_vals = arr[finite_mask]
    finite_frac = finite_vals.size / max(arr.size, 1)

    result: Dict[str, Any] = {
        "is_constant": False,
        "std": 0.0,
        "fill_value_candidates": [],
        "finite_fraction": finite_frac,
    }

    if finite_vals.size == 0:
        result["is_constant"] = True
        return result

    std_val = float(np.std(finite_vals))
    result["std"] = std_val
    result["is_constant"] = std_val < threshold

    # Detect fill-value candidates: values that appear in > 50% of the array
    # Common fill values: 1e20, -9999, -999, 9999, -1e20, 0
    common_fills = [1e20, -1e20, 9.96921e36, -9.96921e36, -9999.0, -999.0, 9999.0]
    fill_candidates = []
    for fv in common_fills:
        count = np.sum(np.isclose(arr, fv, rtol=1e-5, atol=0))
        if count > 0.5 * arr.size:
            fill_candidates.append(fv)

    # Also check the mode for non-standard fill values
    if finite_vals.size > 0:
        unique, counts = np.unique(finite_vals, return_counts=True)
        max_count_idx = np.argmax(counts)
        if counts[max_count_idx] > 0.5 * arr.size:
            mode_val = unique[max_count_idx]
            if mode_val not in fill_candidates:
                fill_candidates.append(float(mode_val))

    result["fill_value_candidates"] = fill_candidates
    return result
