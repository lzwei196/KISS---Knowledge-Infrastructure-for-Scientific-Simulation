"""Locate MARRMoT's managed Octave runtime without a system-wide install."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tomllib


def _managed_prefixes():
    seen = set()
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        for directory in (start, *start.parents):
            config = directory / "kiss.toml"
            if config in seen:
                continue
            seen.add(config)
            if not config.is_file():
                continue
            try:
                raw = tomllib.loads(config.read_text(encoding="utf-8"))
                binaries = Path(raw.get("paths", {}).get("binaries", directory / "binaries"))
            except (OSError, ValueError, TypeError):
                continue
            if not binaries.is_absolute():
                binaries = directory / binaries
            yield binaries / "MARRMoT"
            break


def octave_executable():
    """Use the explicit runtime, this KI's portable runtime, then normal PATH."""
    override = os.environ.get("OCTAVE_EXECUTABLE")
    if override:
        return override
    for prefix in _managed_prefixes():
        for candidate in sorted(prefix.glob("octave/octave-*-w64/mingw64/bin/octave-cli.exe")):
            if candidate.is_file():
                return str(candidate)
    return shutil.which("octave-cli") or shutil.which("octave") or "octave"


def marrmot_source(explicit=None):
    """Return the source folder containing MARRMoT's real model classes."""
    if explicit:
        return str(explicit) if Path(explicit).is_dir() else None
    override = os.environ.get("MARRMOT_PATH")
    candidates = ([Path(override)] if override else [])
    candidates.extend(prefix / "source" / "repo" / "MARRMoT" for prefix in _managed_prefixes())
    candidates.extend((Path("KISSPATH_KI_ROOT/MARRMoT/source/repo/MARRMoT"),
                       Path.home() / "MARRMoT" / "MARRMoT", Path.cwd() / "MARRMoT"))
    for candidate in candidates:
        sentinel = candidate / "Models" / "Model files" / "MARRMoT_model.m"
        if sentinel.is_file():
            return str(candidate)
    return None


def octave_path(value):
    """Escape a path inside a single-quoted MATLAB/Octave string literal."""
    return str(value).replace("\\", "/").replace("'", "''")
