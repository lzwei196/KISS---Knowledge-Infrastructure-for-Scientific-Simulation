"""Regression checks for FSM2's native Windows build and KI preflight paths."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


REPO = Path(__file__).resolve().parents[2]


def load_module(relative_path: str):
    path = REPO / relative_path
    spec = importlib.util.spec_from_file_location(path.stem + "_fsm2_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("platform,binary_name", [("win32", "FSM2.exe"), ("linux", "FSM2")])
def test_compile_moves_actual_native_binary(tmp_path, platform, binary_name):
    wrapper = load_module("models/FSM2/tools/run_fsm2.py")
    source = tmp_path / "source" / "repo"
    (source / "src").mkdir(parents=True)

    def compiler(argv, **kwargs):
        # This is the actual MinGW naming behavior which the old wrapper lost.
        assert argv[argv.index("-o") + 1] == binary_name
        assert argv.index("FSM2_MODULES.F90") < argv.index("FSM2.F90")
        assert "FSM2_PREPNC.F90" not in argv
        (Path(kwargs["cwd"]) / binary_name).write_bytes(b"compiled-product")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch.object(wrapper.sys, "platform", platform), patch.object(wrapper.subprocess, "run", compiler):
        product = Path(wrapper.compile_fsm2(str(source), compiler="private-gfortran"))
    assert product == source / binary_name
    assert product.read_bytes() == b"compiled-product"
    assert not (source / "src" / binary_name).exists()


@pytest.mark.parametrize("relative_path", ["models/FSM2/tools/run_fsm2.py", "models/FSM2/preflight_check.py"])
def test_windows_prefers_exe_and_retains_suffix_free_fallback(tmp_path, relative_path):
    module = load_module(relative_path)
    with patch.object(module.sys, "platform", "win32"):
        assert module.resolve_binary(tmp_path) == tmp_path / "FSM2.exe"
        (tmp_path / "FSM2").write_bytes(b"legacy")
        assert module.resolve_binary(tmp_path) == tmp_path / "FSM2"
        (tmp_path / "FSM2.exe").write_bytes(b"native")
        assert module.resolve_binary(tmp_path) == tmp_path / "FSM2.exe"


def test_compile_failure_cannot_claim_existing_product(tmp_path):
    wrapper = load_module("models/FSM2/tools/run_fsm2.py")
    (tmp_path / "src").mkdir()
    (tmp_path / "FSM2.exe").write_bytes(b"old-product")
    failure = SimpleNamespace(returncode=1, stdout="", stderr="compiler failed")
    with patch.object(wrapper.subprocess, "run", return_value=failure):
        with pytest.raises(RuntimeError, match="compiler failed"):
            wrapper.compile_fsm2(str(tmp_path))


def test_relinked_preflight_uses_canonical_source_tree(tmp_path):
    preflight = REPO / "models/FSM2/preflight_check.py"
    source = tmp_path / "binaries" / "FSM2" / "source" / "repo"
    source.mkdir(parents=True)
    (source / "FSM2.exe").write_bytes(b"native")
    rewritten = preflight.read_text(encoding="utf-8").replace(
        "KISSPATH_BINARIES", (tmp_path / "binaries").as_posix())
    namespace = {"__file__": str(preflight), "__name__": "fsm2_relinked_test"}
    exec(compile(rewritten, str(preflight), "exec"), namespace)
    assert namespace["SOURCE_DIR"] == source
    assert namespace["BINARY"] == source / "FSM2.exe"
