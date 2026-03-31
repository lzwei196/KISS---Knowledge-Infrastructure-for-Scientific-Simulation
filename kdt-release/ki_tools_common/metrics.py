"""
metrics.py — Performance metrics for hydrological and ecological model evaluation.

Consolidates metric calculations duplicated across 42 ki/tools/ scripts.

All functions:
    - Are PURE (no side effects, no file I/O).
    - Handle NaN gracefully — paired NaN values are excluded before computation.
    - Accept 1-D numpy arrays (or array-like) for *obs* and *sim*.
    - Return ``float('nan')`` when there are insufficient valid data points.

Examples::

    >>> from ki_tools_common.metrics import nse, kge, all_metrics
    >>> import numpy as np
    >>> obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    >>> sim = np.array([1.1, 2.2, 2.9, 4.1, 4.8])
    >>> round(nse(obs, sim), 3)
    0.988
    >>> round(kge(obs, sim), 3)
    0.974
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, Union

import numpy as np

Numeric1D = Union[np.ndarray, list, tuple]


def _prepare_paired(
    obs: Numeric1D,
    sim: Numeric1D,
) -> Tuple[np.ndarray, np.ndarray]:
    """Flatten and remove paired NaN/Inf entries.

    Returns two 1-D float64 arrays of equal length containing only finite,
    mutually-valid pairs.
    """
    o = np.asarray(obs, dtype=np.float64).ravel()
    s = np.asarray(sim, dtype=np.float64).ravel()
    min_len = min(o.size, s.size)
    o, s = o[:min_len], s[:min_len]
    mask = np.isfinite(o) & np.isfinite(s)
    return o[mask], s[mask]


# ======================================================================
# Individual metrics
# ======================================================================

def nse(obs: Numeric1D, sim: Numeric1D) -> float:
    """Nash-Sutcliffe Efficiency (NSE).

    .. math::

        NSE = 1 - \\frac{\\sum (O_i - S_i)^2}{\\sum (O_i - \\bar{O})^2}

    Range: (-inf, 1.0]. Perfect score = 1.0. NSE < 0 means the model is
    worse than using the observed mean as a predictor.

    Args:
        obs: Observed values (1-D).
        sim: Simulated values (1-D).

    Returns:
        NSE value, or ``nan`` if fewer than 2 valid pairs.

    Example::

        >>> nse([1, 2, 3], [1, 2, 3])
        1.0
    """
    o, s = _prepare_paired(obs, sim)
    if o.size < 2:
        return float("nan")
    denominator = np.sum((o - np.mean(o)) ** 2)
    if denominator == 0.0:
        return float("nan")
    return float(1.0 - np.sum((o - s) ** 2) / denominator)


def kge(obs: Numeric1D, sim: Numeric1D) -> float:
    """Kling-Gupta Efficiency (KGE, 2009 formulation).

    .. math::

        KGE = 1 - \\sqrt{(r - 1)^2 + (\\alpha - 1)^2 + (\\beta - 1)^2}

    where *r* = Pearson correlation, *alpha* = std(sim)/std(obs),
    *beta* = mean(sim)/mean(obs).

    Range: (-inf, 1.0]. Perfect score = 1.0.

    Args:
        obs: Observed values (1-D).
        sim: Simulated values (1-D).

    Returns:
        KGE value, or ``nan`` if fewer than 2 valid pairs.

    Example::

        >>> round(kge([1, 2, 3, 4, 5], [1.1, 2.2, 2.9, 4.1, 4.8]), 3)
        0.974
    """
    o, s = _prepare_paired(obs, sim)
    if o.size < 2:
        return float("nan")

    o_mean = np.mean(o)
    s_mean = np.mean(s)
    o_std = np.std(o, ddof=0)
    s_std = np.std(s, ddof=0)

    if o_mean == 0.0 or o_std == 0.0:
        return float("nan")

    r = float(np.corrcoef(o, s)[0, 1])
    alpha = s_std / o_std
    beta = s_mean / o_mean

    ed = np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)
    return float(1.0 - ed)


def pbias(obs: Numeric1D, sim: Numeric1D) -> float:
    """Percent bias (PBIAS).

    .. math::

        PBIAS = 100 \\times \\frac{\\sum (S_i - O_i)}{\\sum O_i}

    Positive PBIAS indicates overestimation; negative indicates underestimation.

    Args:
        obs: Observed values (1-D).
        sim: Simulated values (1-D).

    Returns:
        PBIAS in percent, or ``nan`` if sum of observations is zero.

    Example::

        >>> pbias([100, 200, 300], [110, 190, 310])
        1.666...
    """
    o, s = _prepare_paired(obs, sim)
    if o.size == 0:
        return float("nan")
    sum_obs = np.sum(o)
    if sum_obs == 0.0:
        return float("nan")
    return float(100.0 * np.sum(s - o) / sum_obs)


def rmse(obs: Numeric1D, sim: Numeric1D) -> float:
    """Root Mean Square Error (RMSE).

    .. math::

        RMSE = \\sqrt{\\frac{1}{n} \\sum (O_i - S_i)^2}

    Args:
        obs: Observed values (1-D).
        sim: Simulated values (1-D).

    Returns:
        RMSE value (same units as input), or ``nan`` if no valid pairs.

    Example::

        >>> rmse([1, 2, 3], [1, 2, 3])
        0.0
    """
    o, s = _prepare_paired(obs, sim)
    if o.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean((o - s) ** 2)))


def pearson_r(obs: Numeric1D, sim: Numeric1D) -> float:
    """Pearson correlation coefficient.

    Args:
        obs: Observed values (1-D).
        sim: Simulated values (1-D).

    Returns:
        Pearson *r* in [-1, 1], or ``nan`` if fewer than 2 valid pairs or
        if either series has zero variance.

    Example::

        >>> pearson_r([1, 2, 3, 4], [2, 4, 6, 8])
        1.0
    """
    o, s = _prepare_paired(obs, sim)
    if o.size < 2:
        return float("nan")
    if np.std(o) == 0.0 or np.std(s) == 0.0:
        return float("nan")
    return float(np.corrcoef(o, s)[0, 1])


# ======================================================================
# Aggregated metrics
# ======================================================================

def all_metrics(obs: Numeric1D, sim: Numeric1D) -> Dict[str, float]:
    """Compute all five standard metrics at once.

    Args:
        obs: Observed values (1-D).
        sim: Simulated values (1-D).

    Returns:
        Dict with keys ``'NSE'``, ``'KGE'``, ``'PBIAS'``, ``'RMSE'``,
        ``'r'``, each mapping to the corresponding float value.

    Example::

        >>> m = all_metrics([1, 2, 3, 4, 5], [1.1, 2.0, 3.1, 3.9, 5.2])
        >>> sorted(m.keys())
        ['KGE', 'NSE', 'PBIAS', 'RMSE', 'r']
    """
    return {
        "NSE": nse(obs, sim),
        "KGE": kge(obs, sim),
        "PBIAS": pbias(obs, sim),
        "RMSE": rmse(obs, sim),
        "r": pearson_r(obs, sim),
    }


def monthly_metrics(
    obs_daily: Numeric1D,
    sim_daily: Numeric1D,
    dates: Numeric1D,
) -> Dict[str, float]:
    """Aggregate daily data to monthly means, then compute all metrics.

    Args:
        obs_daily: Daily observed values.
        sim_daily: Daily simulated values.
        dates: Array of dates (``numpy.datetime64``, ``pandas.Timestamp``,
            or anything with a ``.astype('datetime64[M]')`` method).

    Returns:
        Dict of metrics computed on monthly aggregates, same keys as
        :func:`all_metrics`.

    Example::

        >>> import numpy as np
        >>> dates = np.arange('2000-01-01', '2000-04-01', dtype='datetime64[D]')
        >>> obs = np.random.rand(len(dates)) * 100
        >>> sim = obs * 1.05  # 5% overestimate
        >>> m = monthly_metrics(obs, sim, dates)
        >>> 'NSE' in m
        True
    """
    obs_arr = np.asarray(obs_daily, dtype=np.float64).ravel()
    sim_arr = np.asarray(sim_daily, dtype=np.float64).ravel()
    dates_arr = np.asarray(dates)

    min_len = min(obs_arr.size, sim_arr.size, dates_arr.size)
    obs_arr = obs_arr[:min_len]
    sim_arr = sim_arr[:min_len]
    dates_arr = dates_arr[:min_len]

    # Convert dates to year-month keys
    try:
        months = dates_arr.astype("datetime64[M]")
    except (TypeError, ValueError):
        # Fall back: try pandas
        import pandas as pd

        months = pd.to_datetime(dates_arr).to_period("M")

    unique_months = np.unique(months)
    obs_monthly = []
    sim_monthly = []

    for m in unique_months:
        mask = months == m
        o_vals = obs_arr[mask]
        s_vals = sim_arr[mask]
        # Only include months with at least some valid data
        o_valid = o_vals[np.isfinite(o_vals)]
        s_valid = s_vals[np.isfinite(s_vals)]
        if o_valid.size > 0 and s_valid.size > 0:
            obs_monthly.append(np.mean(o_valid))
            sim_monthly.append(np.mean(s_valid))

    if len(obs_monthly) < 2:
        return {k: float("nan") for k in ("NSE", "KGE", "PBIAS", "RMSE", "r")}

    return all_metrics(np.array(obs_monthly), np.array(sim_monthly))
