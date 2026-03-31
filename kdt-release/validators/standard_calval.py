#!/usr/bin/env python3
"""
standard_calval.py -- Standard calibration/validation period definitions and
helper functions for the Knowledge Dissection Toolkit.

Default periods (configurable):
    spinup:      Year 1         (discard from all metrics)
    calibration: Years 2-6      (optimize parameters ONLY on this)
    validation:  Years 7-11     (evaluate generalization on this)

The default values below correspond to a 1980-1990 test period. Override them
by calling ``set_periods()`` or by passing custom dates to the functions.

Usage as a library::

    from validators.standard_calval import (
        split_data, compute_calval_metrics, calval_objective,
        set_periods,
    )

    # Option A: use defaults (1980-1990)
    metrics = compute_calval_metrics(dates, obs, sim)

    # Option B: set custom periods globally
    set_periods(
        spinup_year=2000,
        cal_start='2001-01-01', cal_end='2005-12-31',
        val_start='2006-01-01', val_end='2010-12-31',
    )
    metrics = compute_calval_metrics(dates, obs, sim)

Usage from command line (demo)::

    python standard_calval.py --demo
"""

import datetime as _dt
import numpy as np

# ---------------------------------------------------------------------------
# Standard period definitions (defaults; override with set_periods())
# ---------------------------------------------------------------------------
SPINUP_YEAR = 1980

CAL_START = _dt.date(1981, 1, 1)
CAL_END   = _dt.date(1985, 12, 31)

VAL_START = _dt.date(1986, 1, 1)
VAL_END   = _dt.date(1990, 12, 31)

FULL_START = CAL_START
FULL_END   = VAL_END


def set_periods(spinup_year=None, cal_start=None, cal_end=None,
                val_start=None, val_end=None):
    """Override the default calibration/validation periods.

    Parameters
    ----------
    spinup_year : int, optional
        Year to discard as spinup.
    cal_start, cal_end : str or datetime.date, optional
        Calibration period boundaries (inclusive). Strings must be 'YYYY-MM-DD'.
    val_start, val_end : str or datetime.date, optional
        Validation period boundaries (inclusive).

    Example::

        set_periods(
            spinup_year=2000,
            cal_start='2001-01-01', cal_end='2005-12-31',
            val_start='2006-01-01', val_end='2010-12-31',
        )
    """
    global SPINUP_YEAR, CAL_START, CAL_END, VAL_START, VAL_END, FULL_START, FULL_END

    def _to_date(v):
        if isinstance(v, str):
            return _dt.date.fromisoformat(v)
        return v

    if spinup_year is not None:
        SPINUP_YEAR = int(spinup_year)
    if cal_start is not None:
        CAL_START = _to_date(cal_start)
    if cal_end is not None:
        CAL_END = _to_date(cal_end)
    if val_start is not None:
        VAL_START = _to_date(val_start)
    if val_end is not None:
        VAL_END = _to_date(val_end)

    FULL_START = CAL_START
    FULL_END = VAL_END


# ---------------------------------------------------------------------------
# Helper: convert flexible date inputs to numpy datetime64 arrays
# ---------------------------------------------------------------------------
def _to_date_array(dates):
    """Convert dates to a 1-D numpy array of datetime.date objects.

    Accepts:
      - list/array of datetime.date
      - list/array of datetime.datetime
      - list/array of np.datetime64
      - list/array of strings 'YYYY-MM-DD'
      - pandas DatetimeIndex (if pandas is available)
    """
    if hasattr(dates, 'date'):
        # pandas Timestamp / DatetimeIndex
        try:
            return np.array([d.date() for d in dates])
        except TypeError:
            return np.array([dates.date()])

    out = []
    for d in dates:
        if isinstance(d, _dt.datetime):
            out.append(d.date())
        elif isinstance(d, _dt.date):
            out.append(d)
        elif isinstance(d, np.datetime64):
            ts = (d - np.datetime64('1970-01-01', 'D')).astype(int)
            out.append(_dt.date(1970, 1, 1) + _dt.timedelta(days=int(ts)))
        elif isinstance(d, str):
            out.append(_dt.date.fromisoformat(d))
        else:
            raise TypeError(f"Cannot convert {type(d)} to date")
    return np.array(out)


# ---------------------------------------------------------------------------
# split_data
# ---------------------------------------------------------------------------
def split_data(dates, obs, sim, cal_start=None, cal_end=None,
               val_start=None, val_end=None):
    """Split time series into calibration and validation subsets.

    Parameters
    ----------
    dates : array-like
        Date stamps for each time step (length N).
    obs : array-like, shape (N,)
        Observed values (e.g. discharge in m3/s).
    sim : array-like, shape (N,)
        Simulated values, same length as *obs*.
    cal_start, cal_end : datetime.date, optional
        Override module-level calibration period.
    val_start, val_end : datetime.date, optional
        Override module-level validation period.

    Returns
    -------
    dict with keys:
        'cal_dates', 'cal_obs', 'cal_sim',
        'val_dates', 'val_obs', 'val_sim'
    """
    _cal_start = cal_start if cal_start is not None else CAL_START
    _cal_end = cal_end if cal_end is not None else CAL_END
    _val_start = val_start if val_start is not None else VAL_START
    _val_end = val_end if val_end is not None else VAL_END

    dates = _to_date_array(dates)
    obs = np.asarray(obs, dtype=float)
    sim = np.asarray(sim, dtype=float)

    if not (len(dates) == len(obs) == len(sim)):
        raise ValueError(
            f"Length mismatch: dates={len(dates)}, obs={len(obs)}, sim={len(sim)}"
        )

    cal_mask = np.array([(_cal_start <= d <= _cal_end) for d in dates])
    val_mask = np.array([(_val_start <= d <= _val_end) for d in dates])

    return {
        'cal_dates': dates[cal_mask],
        'cal_obs':   obs[cal_mask],
        'cal_sim':   sim[cal_mask],
        'val_dates': dates[val_mask],
        'val_obs':   obs[val_mask],
        'val_sim':   sim[val_mask],
    }


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------
def _nse(obs, sim):
    """Nash-Sutcliffe Efficiency."""
    obs, sim = np.asarray(obs), np.asarray(sim)
    mask = np.isfinite(obs) & np.isfinite(sim)
    o, s = obs[mask], sim[mask]
    if len(o) < 2:
        return np.nan
    ss_res = np.sum((o - s) ** 2)
    ss_tot = np.sum((o - np.mean(o)) ** 2)
    if ss_tot == 0:
        return np.nan
    return 1.0 - ss_res / ss_tot


def _kge(obs, sim):
    """Kling-Gupta Efficiency (2009 formulation)."""
    obs, sim = np.asarray(obs), np.asarray(sim)
    mask = np.isfinite(obs) & np.isfinite(sim)
    o, s = obs[mask], sim[mask]
    if len(o) < 2:
        return np.nan
    r = np.corrcoef(o, s)[0, 1]
    alpha = np.std(s) / np.std(o) if np.std(o) > 0 else np.nan
    beta = np.mean(s) / np.mean(o) if np.mean(o) != 0 else np.nan
    return 1.0 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)


def _pbias(obs, sim):
    """Percent bias (positive = overestimation)."""
    obs, sim = np.asarray(obs), np.asarray(sim)
    mask = np.isfinite(obs) & np.isfinite(sim)
    o, s = obs[mask], sim[mask]
    if np.sum(o) == 0:
        return np.nan
    return 100.0 * np.sum(s - o) / np.sum(o)


def _r(obs, sim):
    """Pearson correlation coefficient."""
    obs, sim = np.asarray(obs), np.asarray(sim)
    mask = np.isfinite(obs) & np.isfinite(sim)
    o, s = obs[mask], sim[mask]
    if len(o) < 2:
        return np.nan
    return np.corrcoef(o, s)[0, 1]


def _compute_metrics(obs, sim):
    """Return a dict of standard metrics for one period."""
    return {
        'NSE':   round(_nse(obs, sim), 4),
        'KGE':   round(_kge(obs, sim), 4),
        'PBIAS': round(_pbias(obs, sim), 2),
        'r':     round(_r(obs, sim), 4),
        'n':     int(np.sum(np.isfinite(obs) & np.isfinite(sim))),
    }


def compute_calval_metrics(dates, obs, sim, **kwargs):
    """Compute standard hydrological metrics for calibration and validation
    periods separately, plus the full combined period.

    Parameters
    ----------
    dates, obs, sim : array-like
        Same as ``split_data``.
    **kwargs :
        Optional ``cal_start``, ``cal_end``, ``val_start``, ``val_end``
        passed through to ``split_data``.

    Returns
    -------
    dict with keys 'calibration', 'validation', 'full', each containing a
    metrics dict with NSE, KGE, PBIAS, r, n.
    """
    sp = split_data(dates, obs, sim, **kwargs)
    return {
        'calibration': _compute_metrics(sp['cal_obs'], sp['cal_sim']),
        'validation':  _compute_metrics(sp['val_obs'], sp['val_sim']),
        'full':        _compute_metrics(
            np.concatenate([sp['cal_obs'], sp['val_obs']]),
            np.concatenate([sp['cal_sim'], sp['val_sim']]),
        ),
    }


# ---------------------------------------------------------------------------
# Calibration objective wrapper
# ---------------------------------------------------------------------------
def calval_objective(params, model_func, forcing, obs, dates,
                     metric='NSE', maximize=True, **kwargs):
    """Objective function wrapper for scipy.optimize that ONLY uses the
    calibration period data in the objective.

    Parameters
    ----------
    params : array-like
        Parameter vector being optimized.
    model_func : callable
        ``model_func(params, forcing)`` -> simulated array of same length as
        *dates*.
    forcing : object
        Whatever *model_func* needs. Passed through unchanged.
    obs : array-like, shape (N,)
        Full observed time series (may include spinup + cal + val).
    dates : array-like, shape (N,)
        Corresponding dates.
    metric : str, default 'NSE'
        Which metric to use. One of 'NSE', 'KGE'.
    maximize : bool, default True
        If True, returns ``-metric`` for minimization optimizers.
    **kwargs :
        Optional ``cal_start``, ``cal_end``, ``val_start``, ``val_end``.

    Returns
    -------
    float
        Scalar objective value.
    """
    sim = model_func(params, forcing)
    sp = split_data(dates, obs, sim, **kwargs)

    cal_obs = sp['cal_obs']
    cal_sim = sp['cal_sim']

    if metric == 'NSE':
        value = _nse(cal_obs, cal_sim)
    elif metric == 'KGE':
        value = _kge(cal_obs, cal_sim)
    else:
        raise ValueError(f"Unsupported metric: {metric!r}. Use 'NSE' or 'KGE'.")

    if np.isnan(value):
        return 1e6  # penalty for degenerate solutions

    if maximize:
        return -value   # minimize negative metric = maximize metric
    return 1.0 - value


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------
def _demo():
    """Generate a synthetic example and show the split/metrics."""
    np.random.seed(42)

    # synthetic daily dates for the default period
    start = _dt.date(SPINUP_YEAR, 1, 1)
    n_days = (VAL_END - start).days + 1
    dates = [start + _dt.timedelta(days=i) for i in range(n_days)]

    # synthetic discharge (seasonal + noise)
    t = np.arange(n_days)
    obs = 500 + 400 * np.sin(2 * np.pi * t / 365.25 - np.pi / 2) + \
        np.random.normal(0, 100, n_days)
    obs = np.maximum(obs, 10)
    sim = obs * (1.0 + np.random.normal(0, 0.15, n_days))
    sim = np.maximum(sim, 0)

    metrics = compute_calval_metrics(dates, obs, sim)

    print("=" * 60)
    print("  standard_calval.py -- Demo output")
    print("=" * 60)
    print(f"\n  Standard periods:")
    print(f"    Spinup:      {SPINUP_YEAR}")
    print(f"    Calibration: {CAL_START} to {CAL_END}")
    print(f"    Validation:  {VAL_START} to {VAL_END}")

    for period_name, m in metrics.items():
        print(f"\n  {period_name.upper()} metrics:")
        for k, v in m.items():
            print(f"    {k:>6s} = {v}")

    print()
    return 0


if __name__ == '__main__':
    import sys
    if '--demo' in sys.argv:
        sys.exit(_demo())
    else:
        print("Usage: python standard_calval.py --demo")
        print()
        print("This module is primarily a library.  Import it as:")
        print("  from validators.standard_calval import (")
        print("      split_data, compute_calval_metrics, calval_objective,")
        print("      set_periods,")
        print("  )")
        sys.exit(0)
