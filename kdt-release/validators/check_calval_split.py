#!/usr/bin/env python3
"""
check_calval_split.py -- Preflight validator that checks whether a model's
stage_log.json enforces proper calibration/validation period separation.

Detects data leakage where models calibrate on 1981-1990 and report
"validation" metrics on the same period, inflating NSE by ~0.10-0.15.

Statuses:
    PASS  -- Separate cal and val periods declared, with non-overlapping
             date ranges and separate metrics reported for each.
    WARN  -- Ambiguous: some split information present but incomplete
             (e.g. separate periods declared but only full-period metrics).
    FAIL  -- No cal/val split: model calibrates and evaluates on the same
             period, or only "full period" metrics are reported after
             calibration.
    SKIP  -- No s8_validation stage, or validation not completed, or model
             is not a calibrated type (uncalibrated / negative NSE / no
             calibration performed).

Usage:
    # Check one model
    python check_calval_split.py MODEL_NAME --work-dir /path/to/work/

    # Check all models
    python check_calval_split.py --all --work-dir /path/to/work/

    # JSON output
    python check_calval_split.py --all --work-dir /path/to/work/ --json

    # Only show failures
    python check_calval_split.py --all --work-dir /path/to/work/ --failures-only
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WORK_DIR = None  # Must be specified via --work-dir or passed to check_model()

# Standard periods for reference
STD_CAL = (1981, 1985)
STD_VAL = (1986, 1990)


# ---------------------------------------------------------------------------
# Period parsing helpers
# ---------------------------------------------------------------------------
def _parse_year_range(text):
    """Extract (start_year, end_year) from strings like '1981-1985',
    '1981-01-01 to 1985-12-31', '1980', '1996-01 to 2014-12 (full)', etc.
    Returns None on failure."""
    if text is None:
        return None
    text = str(text).strip()

    # Strip trailing parenthetical annotations like "(full)"
    text = re.sub(r'\s*\(.*?\)\s*$', '', text)

    # "1981-1985" or "1981 - 1985"
    m = re.match(r'^(\d{4})\s*[-\u2013\u2014]\s*(\d{4})$', text)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # "1981-01-01 to 1985-12-31" or "1996-01 to 2014-12"
    m = re.match(r'^(\d{4})-\d{2}(?:-\d{2})?\s+to\s+(\d{4})-\d{2}(?:-\d{2})?$', text)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # Single year "1980"
    m = re.match(r'^(\d{4})$', text)
    if m:
        y = int(m.group(1))
        return (y, y)

    return None


def _ranges_overlap(r1, r2):
    """True if two (start, end) year ranges overlap."""
    if r1 is None or r2 is None:
        return False
    return r1[0] <= r2[1] and r2[0] <= r1[1]


# ---------------------------------------------------------------------------
# Core checker
# ---------------------------------------------------------------------------
def check_model(model_name, work_dir=None):
    """Check a single model's stage_log.json for cal/val split compliance.

    Returns
    -------
    dict with keys:
        model     : str
        status    : 'PASS' | 'WARN' | 'FAIL' | 'SKIP'
        reasons   : list[str]  -- human-readable explanation(s)
        details   : dict       -- parsed period / metric info
    """
    if work_dir is None:
        work_dir = WORK_DIR

    work_dir = Path(work_dir)
    stage_log_path = work_dir / model_name / 'stage_log.json'

    result = {
        'model': model_name,
        'status': 'SKIP',
        'reasons': [],
        'details': {},
    }

    # --- Load stage_log.json ---
    if not stage_log_path.exists():
        result['reasons'].append(f'No stage_log.json at {stage_log_path}')
        return result

    try:
        with open(stage_log_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        result['reasons'].append(f'Cannot read stage_log.json: {exc}')
        return result

    # --- Locate s8_validation (or s9_revalidation as override) ---
    # Some models have a separate s9_revalidation that supersedes s8.
    # Prefer s9 if it exists and has a proper cal/val split, otherwise use s8.
    s8 = None
    stages = data.get('stages', data)  # handle both nested and flat layouts

    # Collect all validation stages
    s8_candidate = stages.get('s8_validation')
    s9_candidate = stages.get('s9_revalidation')

    # Prefer s9 if completed (it typically is a basin-specific re-validation)
    if isinstance(s9_candidate, dict) and s9_candidate.get('status') == 'completed':
        s8 = s9_candidate
        result['details']['stage_used'] = 's9_revalidation'
    elif isinstance(s8_candidate, dict):
        s8 = s8_candidate
        result['details']['stage_used'] = 's8_validation'

    if s8 is None:
        result['reasons'].append('No s8_validation stage found')
        return result

    if s8.get('status') != 'completed':
        result['reasons'].append(
            f"Validation stage status is {s8.get('status')!r}, not 'completed'"
        )
        return result

    # --- Gather information about periods ---
    cal_range = None
    val_range = None
    full_range = None
    has_cal_metrics = False
    has_val_metrics = False
    has_full_only_metrics = False
    was_calibrated = False

    # Check for explicit period fields (various naming conventions)
    period_cal_keys = ['period_calibration', 'calibration_period', 'cal_period']
    period_val_keys = ['period_validation', 'validation_period', 'val_period']
    period_full_keys = ['period']

    for k in period_cal_keys:
        if k in s8:
            cal_range = _parse_year_range(s8[k])
            break

    for k in period_val_keys:
        if k in s8:
            val_range = _parse_year_range(s8[k])
            break

    # Check nested 'period' dict (e.g. HydroCNHS style)
    if isinstance(s8.get('period'), dict):
        p = s8['period']
        if 'calibration' in p and cal_range is None:
            cal_range = _parse_year_range(p['calibration'])
        if 'validation' in p and val_range is None:
            val_range = _parse_year_range(p['validation'])
        if 'spinup' in p:
            result['details']['spinup'] = str(p['spinup'])
    elif isinstance(s8.get('period'), str):
        full_range = _parse_year_range(s8['period'])

    # Check nested 'periods' dict (e.g. CLASSIC s9 style)
    if isinstance(s8.get('periods'), dict):
        p = s8['periods']
        if 'calibration' in p and cal_range is None:
            cal_range = _parse_year_range(p['calibration'])
        if 'validation' in p and val_range is None:
            val_range = _parse_year_range(p['validation'])
        if 'spinup' in p:
            result['details']['spinup'] = str(p['spinup'])

    # Check nested 'calibration' dict for period info (e.g. DayCent style)
    cal_dict = s8.get('calibration', {})
    if isinstance(cal_dict, dict):
        for k in ('calibration_period', 'cal_period'):
            if k in cal_dict and cal_range is None:
                cal_range = _parse_year_range(cal_dict[k])
        for k in ('validation_period', 'val_period'):
            if k in cal_dict and val_range is None:
                val_range = _parse_year_range(cal_dict[k])

    # Check for calibration evidence
    explicitly_uncalibrated = False
    if 'calibration' in s8 or 'calibrated_parameters' in s8:
        was_calibrated = True
    if 'parameters' in s8 and isinstance(s8['parameters'], dict):
        was_calibrated = True

    # Check model_setup and text fields for "uncalibrated" override
    # Also check model_description for calibration signals
    for field_name in ('model_setup', 'tier_justification', 'model_description'):
        text = str(s8.get(field_name, '')).lower()
        if 'uncalibrated' in text or 'un-calibrated' in text:
            explicitly_uncalibrated = True
        if any(kw in text for kw in
               ('calibrated via', 'calibrated with', 'calibrated on')):
            was_calibrated = True

    # Check findings/notes for calibration keywords
    for field_name in ('findings', 'notes'):
        entries = s8.get(field_name, [])
        if isinstance(entries, list):
            text = ' '.join(str(e) for e in entries).lower()
        else:
            text = str(entries).lower()
        # Look for strong signals that the model WAS actually calibrated
        # (not just mentions of calibration in passing)
        if any(kw in text for kw in
               ('differential_evolution', 'grid search', 'scipy.optimize',
                'parameters calibrated', 'calibrated on', 'calibrated via',
                'calibrated with')):
            was_calibrated = True
        if 'uncalibrated' in text or 'un-calibrated' in text:
            explicitly_uncalibrated = True

    if isinstance(cal_dict, dict) and cal_dict.get('method'):
        was_calibrated = True

    # If explicitly stated as uncalibrated, override
    if explicitly_uncalibrated and not (
        'calibrated_parameters' in s8 or
        (isinstance(cal_dict, dict) and cal_dict.get('method'))
    ):
        was_calibrated = False

    # Check for separate cal/val metrics
    metrics = s8.get('metrics', {})

    # Also check for separate top-level metrics dicts (RHESSys style)
    if 'metrics_validation' in s8 or 'metrics_val' in s8:
        has_val_metrics = True
    if 'metrics_calibration' in s8 or 'metrics_cal' in s8:
        has_cal_metrics = True

    if isinstance(metrics, dict):
        # Filter out nested dicts (e.g. GPP_monthly: {NSE: 0.466}) -- these
        # are variable-specific metrics, not period-specific metrics.
        scalar_keys = [k for k, v in metrics.items()
                       if isinstance(v, (int, float))]
        metric_keys_lower = [k.lower() for k in scalar_keys]

        # Also check for period-tagged sub-dicts (CLASSIC s9 style):
        # metrics.calibration_daily, metrics.validation_daily, etc.
        subdict_keys_lower = [k.lower() for k, v in metrics.items()
                              if isinstance(v, dict)]
        if any('calibration' in k or 'cal_' in k for k in subdict_keys_lower):
            has_cal_metrics = True
        if any('validation' in k or 'val_' in k for k in subdict_keys_lower):
            has_val_metrics = True

        # Separate cal metrics: NSE_cal, KGE_cal, etc.
        if any('_cal' in k for k in metric_keys_lower):
            has_cal_metrics = True
        # Separate val metrics: NSE_val, KGE_val, NSE_daily_val, etc.
        if any('_val' in k for k in metric_keys_lower):
            has_val_metrics = True
        # Only full-period metrics: NSE, KGE without _cal/_val suffix
        base_metric_keys = {'nse', 'kge', 'pbias', 'r', 'rmse'}
        has_base_metrics = bool(
            set(metric_keys_lower) & base_metric_keys
        )

        if has_base_metrics and not has_val_metrics:
            has_full_only_metrics = True

    # Store details
    result['details'] = {
        'cal_range': f"{cal_range[0]}-{cal_range[1]}" if cal_range else None,
        'val_range': f"{val_range[0]}-{val_range[1]}" if val_range else None,
        'full_range': f"{full_range[0]}-{full_range[1]}" if full_range else None,
        'was_calibrated': was_calibrated,
        'has_cal_metrics': has_cal_metrics,
        'has_val_metrics': has_val_metrics,
        'has_full_only_metrics': has_full_only_metrics,
    }

    # --- Check for negative NSE / uncalibrated models -> SKIP ---
    # Extract top-level scalar NSE (skip nested dicts like GPP_monthly)
    nse_val = None
    for nse_key in ('NSE', 'nse'):
        v = metrics.get(nse_key)
        if isinstance(v, (int, float)):
            nse_val = v
            break
    if isinstance(nse_val, (int, float)) and nse_val < 0:
        result['status'] = 'SKIP'
        result['reasons'].append(
            f'Negative NSE ({nse_val:.3f}) suggests uncalibrated or '
            f'structurally poor fit -- cal/val split check not applicable'
        )
        return result

    if not was_calibrated:
        # If there is no evidence of calibration, the model either ran
        # uncalibrated defaults or is a non-calibrated model type.  The
        # cal/val split concern does not apply.
        flags = s8.get('flags', {})
        if flags.get('needs_revalidation') or flags.get('parameter_mismatch'):
            result['status'] = 'SKIP'
            result['reasons'].append(
                'Model appears uncalibrated (needs_revalidation / '
                'parameter_mismatch flagged)'
            )
            return result

    # --- Decision logic ---

    # PASS: separate cal and val periods, non-overlapping, with val metrics
    if cal_range and val_range:
        if _ranges_overlap(cal_range, val_range):
            result['status'] = 'FAIL'
            result['reasons'].append(
                f'Calibration ({cal_range[0]}-{cal_range[1]}) and validation '
                f'({val_range[0]}-{val_range[1]}) periods OVERLAP -- '
                f'data leakage'
            )
        elif has_val_metrics:
            result['status'] = 'PASS'
            result['reasons'].append(
                f'Proper split: cal={cal_range[0]}-{cal_range[1]}, '
                f'val={val_range[0]}-{val_range[1]}, '
                f'separate val metrics reported'
            )
        else:
            result['status'] = 'WARN'
            result['reasons'].append(
                f'Periods are split (cal={cal_range[0]}-{cal_range[1]}, '
                f'val={val_range[0]}-{val_range[1]}) but no separate '
                f'validation-period metrics found in metrics dict'
            )
        return result

    # No explicit cal/val split declared
    if was_calibrated:
        # Calibrated model without a declared split
        if has_val_metrics and has_cal_metrics:
            # Metrics exist even though periods are not explicitly declared
            result['status'] = 'WARN'
            result['reasons'].append(
                'Separate cal/val metrics found (e.g. NSE_cal, NSE_val) but '
                'calibration and validation periods not explicitly declared '
                'in stage_log fields'
            )
        elif has_val_metrics:
            # Has val-tagged metrics but no cal range declared -- ambiguous
            # Could mean the model actually did a split but did not record
            # the period boundaries.
            result['status'] = 'WARN'
            result['reasons'].append(
                'Validation-tagged metrics present (e.g. NSE_daily_val) but '
                'no explicit calibration_period/validation_period fields. '
                'Cannot confirm periods are non-overlapping.'
            )
        else:
            # Calibrated, only full-period metrics, no split
            period_str = (
                f"{full_range[0]}-{full_range[1]}" if full_range
                else s8.get('period', 'unknown')
            )
            result['status'] = 'FAIL'
            result['reasons'].append(
                f'Model was calibrated but only reports full-period metrics '
                f'on {period_str} -- likely evaluating on calibration data '
                f'(data leakage). Reported metrics may be inflated by '
                f'~0.10-0.15 NSE.'
            )
        return result

    # Not calibrated (or at least no evidence of it)
    result['status'] = 'SKIP'
    result['reasons'].append(
        'No evidence of calibration found -- cal/val split check '
        'not applicable for uncalibrated runs'
    )
    return result


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------
def find_all_models(work_dir=None):
    """Return sorted list of model directory names that have stage_log.json."""
    if work_dir is None:
        work_dir = WORK_DIR
    work_dir = Path(work_dir)
    models = []
    if not work_dir.is_dir():
        return models
    for entry in sorted(work_dir.iterdir()):
        if entry.is_dir() and (entry / 'stage_log.json').exists():
            models.append(entry.name)
    return models


def check_all(work_dir=None):
    """Run the checker on every model.  Returns list of result dicts."""
    models = find_all_models(work_dir)
    return [check_model(m, work_dir) for m in models]


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------
_STATUS_COLORS = {
    'PASS': '\033[92m',  # green
    'WARN': '\033[93m',  # yellow
    'FAIL': '\033[91m',  # red
    'SKIP': '\033[90m',  # grey
}
_RESET = '\033[0m'


def _colorize(status):
    """Return ANSI-colored status string."""
    if not sys.stdout.isatty():
        return status
    return f"{_STATUS_COLORS.get(status, '')}{status}{_RESET}"


def print_results(results, failures_only=False, show_details=False):
    """Print a formatted summary table."""
    counts = {'PASS': 0, 'WARN': 0, 'FAIL': 0, 'SKIP': 0}
    fail_models = []

    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
        if r['status'] == 'FAIL':
            fail_models.append(r['model'])

    # Header
    print()
    print("=" * 78)
    print("  Cal/Val Split Check -- Knowledge Dissection Toolkit")
    print("=" * 78)
    print()

    # Results table
    for r in results:
        if failures_only and r['status'] not in ('FAIL', 'WARN'):
            continue
        status_str = _colorize(r['status'])
        print(f"  [{status_str:>4s}]  {r['model']:<30s}  {r['reasons'][0] if r['reasons'] else ''}")
        if show_details and len(r['reasons']) > 1:
            for reason in r['reasons'][1:]:
                print(f"         {'':30s}  {reason}")

    # Summary
    print()
    print("-" * 78)
    total = len(results)
    print(f"  Total models checked: {total}")
    print(f"    PASS: {counts['PASS']:3d}  (proper cal/val split)")
    print(f"    WARN: {counts['WARN']:3d}  (ambiguous -- needs review)")
    print(f"    FAIL: {counts['FAIL']:3d}  (data leakage -- cal == val period)")
    print(f"    SKIP: {counts['SKIP']:3d}  (uncalibrated / no s8 / not applicable)")

    if fail_models:
        print()
        print(f"  FAILING MODELS ({len(fail_models)}):")
        for m in fail_models:
            print(f"    - {m}")

    print()
    print("  Recommendation: Use standard_calval.py helpers to enforce")
    print("  proper temporal split in all calibrated models.")
    print("  See: validators/standard_calval.py")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Check cal/val period separation in model stage_log.json files.'
    )
    parser.add_argument(
        'model', nargs='?', default=None,
        help='Model name (subdirectory under --work-dir). Omit for --all.'
    )
    parser.add_argument(
        '--all', action='store_true',
        help='Check all models in the work directory.'
    )
    parser.add_argument(
        '--work-dir', type=str, default=None,
        help='Work directory containing per-model subdirectories with stage_log.json'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output results as JSON.'
    )
    parser.add_argument(
        '--failures-only', action='store_true',
        help='Only show FAIL and WARN results.'
    )
    parser.add_argument(
        '--details', action='store_true',
        help='Show extra detail lines.'
    )

    args = parser.parse_args()
    if args.work_dir:
        work_dir = Path(args.work_dir)
    elif WORK_DIR is not None:
        work_dir = Path(WORK_DIR)
    else:
        print("ERROR: --work-dir is required. Specify the directory containing "
              "per-model subdirectories with stage_log.json files.")
        return 1

    if args.all:
        results = check_all(work_dir)
    elif args.model:
        results = [check_model(args.model, work_dir)]
    else:
        parser.print_help()
        return 1

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_results(results, failures_only=args.failures_only,
                      show_details=args.details)

    # Exit code: 1 if any FAIL
    if any(r['status'] == 'FAIL' for r in results):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
