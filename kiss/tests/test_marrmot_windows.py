"""Portable MARRMoT runtime and generated Octave script regression checks."""

import importlib.util
from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[2] / "models" / "MARRMoT" / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = _load("octave_runtime")
wrapper = _load("run_marrmot")


def test_managed_octave_and_source_do_not_require_system_path(tmp_path, monkeypatch):
    prefix = tmp_path / "binaries" / "MARRMoT"
    executable = prefix / "octave" / "octave-11.3.0-w64" / "mingw64" / "bin" / "octave-cli.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"MZ")
    source = prefix / "source" / "repo" / "MARRMoT"
    sentinel = source / "Models" / "Model files" / "MARRMoT_model.m"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("classdef MARRMoT_model; end", encoding="utf-8")
    (tmp_path / "kiss.toml").write_text("[paths]\nbinaries = 'binaries'\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OCTAVE_EXECUTABLE", raising=False)
    monkeypatch.delenv("MARRMOT_PATH", raising=False)
    monkeypatch.setattr(runtime.shutil, "which", lambda _: None)
    assert Path(runtime.octave_executable()) == executable
    assert Path(runtime.marrmot_source()) == source


def test_octave_script_quotes_windows_and_apostrophe_paths():
    script = wrapper.build_octave_script(
        r"D:\O'Brien\forcing.csv", "m_01_collie1_1p_1s", [100], [0],
        r"D:\O'Brien\MARRMoT", 1, r"D:\O'Brien\out.csv", .1, 6)
    assert "D:/O''Brien/forcing.csv" in script
    assert "D:/O''Brien/MARRMoT" in script
    assert "D:/O''Brien/out.csv" in script
    assert "D:\\O'Brien" not in script


def test_failed_octave_process_is_not_a_present_function(monkeypatch):
    import subprocess
    monkeypatch.setattr(wrapper.subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a, 1, "", "missing DLL"))
    assert not wrapper._octave_has("normcdf")
