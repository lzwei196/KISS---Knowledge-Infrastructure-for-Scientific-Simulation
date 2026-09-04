# -*- mode: python ; coding: utf-8 -*-
"""Reproducible Windows GeoForge Desktop executable."""

from pathlib import Path
import sys
import tomllib

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    copy_metadata,
)


SOURCE = Path(SPECPATH).resolve()
REPO = SOURCE.parent
if sys.version_info >= (3, 13):
    raise RuntimeError(
        "Windows releases must be built with Python 3.11 or 3.12; "
        "pythonnet/WinForms deadlocks under Python 3.13."
    )
with (SOURCE / "pyproject.toml").open("rb") as version_file:
    VERSION = tomllib.load(version_file)["project"]["version"]
ICON = REPO / "assets" / "logo.ico"
KI_TOOLS_SOURCE = REPO / "ki_tools_common"

trust_datas, trust_binaries, trust_hidden = collect_all("truststore")
certifi_datas = collect_data_files("certifi")
webview_hidden = []
calibration_datas = []
for distribution in ("numpy", "PyYAML", "spotpy", "pymoo", "moocore"):
    calibration_datas.extend(copy_metadata(distribution))
calibration_binaries = collect_dynamic_libs("pymoo")
calibration_hidden = [
    "numpy", "scipy", "yaml", "spotpy",
    "pymoo.core.problem", "pymoo.optimize",
    "pymoo.algorithms.moo.nsga2", "pymoo.algorithms.moo.nsga3",
    "pymoo.algorithms.moo.moead", "pymoo.util.ref_dirs",
    "pymoo.functions.compiled.calc_perpendicular_distance",
    "pymoo.functions.compiled.decomposition",
    "pymoo.functions.compiled.mnn",
    "pymoo.functions.compiled.non_dominated_sorting",
    "pymoo.functions.compiled.pruning_cd",
    "pymoo.functions.compiled.stochastic_ranking",
]
harness_hidden = [
    "ki_tools_common",
    "ki_tools_common.harness",
    "ki_tools_common.harness.ki_harness",
    "ki_tools_common.harness.ki_path",
    "ki_tools_common.harness.ki_attention",
    "ki_tools_common.harness.agent_spawn",
    "ki_tools_common.flow",
    "ki_tools_common.flow.states",
    "ki_tools_common.flow.resolve",
    "ki_tools_common.flow.plan",
    "ki_tools_common.flow.approval",
    "ki_tools_common.flow.contracts",
    "ki_tools_common.flow.receipts",
    "ki_tools_common.flow.policy",
    "ki_tools_common.flow.tools",
    "ki_tools_common.flow.build_data",
]

a = Analysis(
    [str(SOURCE / "kiss_entry.py")],
    pathex=[str(SOURCE), str(KI_TOOLS_SOURCE)],
    binaries=[*trust_binaries, *calibration_binaries],
    datas=[
        (str(SOURCE / "kiss_cli" / "web"), "kiss_cli/web"),
        (str(REPO / "models"), "models"),
        (str(REPO / "ki_tools_common"), "ki_tools_common"),
        (str(SOURCE / "vendor" / "agent-calibration-framework"),
         "agent-calibration-framework"),
        (str(SOURCE / "manifests"), "kiss/manifests"),
        (str(REPO / "release-manifest.json"), "."),
        (str(REPO / "DESKTOP_CHANGELOG.md"), "."),
        *trust_datas,
        *certifi_datas,
        *calibration_datas,
    ],
    hiddenimports=[
        *trust_hidden, *webview_hidden, *calibration_hidden, *harness_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch", "torchvision", "torchaudio", "pandas", "matplotlib",
        "PIL", "pyarrow", "IPython", "jedi", "botocore", "boto3",
        "fsspec", "lxml", "dask", "numba", "mpi4py", "pathos",
        "tensorflow", "keras", "cv2", "sklearn", "xarray", "h5py",
        "pyproj", "rasterio", "rioxarray",
        "webview", "pythonnet", "clr", "clr_loader", "PySide6", "qtpy",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GeoForge Desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=f"GeoForge Desktop {VERSION} Windows",
)
