"""
ki_tools_common -- Shared utility library for the Knowledge Dissection Toolkit.

Consolidates duplicated code found across 435+ model tool scripts.
Provides canonical implementations for unit conversions, humidity calculations,
NetCDF helpers, validation checks, performance metrics, I/O helpers, and
forcing-source variable mappings.

Usage::

    from ki_tools_common import units, metrics, humidity, validation
    from ki_tools_common.units import convert, celsius_to_kelvin
    from ki_tools_common.metrics import nse, kge, all_metrics
"""

from ki_tools_common import (
    units,
    humidity,
    netcdf_utils,
    validation,
    metrics,
    io_helpers,
    forcing_sources,
)

__version__ = "0.1.0"

__all__ = [
    "units",
    "humidity",
    "netcdf_utils",
    "validation",
    "metrics",
    "io_helpers",
    "forcing_sources",
]
