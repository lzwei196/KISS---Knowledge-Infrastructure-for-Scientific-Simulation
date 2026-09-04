"""The bundled KI harness must be the server's, relocated — never a hand-restored old copy."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUNDLED = REPO / "ki_tools_common" / "ki_tools_common" / "harness" / "ki_harness.py"
SERVER = Path("/mnt/disk1/Hydrocraft_server/models/ki_tools_common/ki_tools_common/harness/ki_harness.py")


def test_bundled_harness_has_the_current_contract_surface():
    text = BUNDLED.read_text(encoding="utf-8")
    assert "OBLIGATIONS = {" in text, "obligations registry missing (pre-2026-08-20 copy)"
    assert re.search(r"def contract\(.*mode: str \| None = None", text, re.S), "contract() lacks mode="
    assert "WHAT THIS MODEL PRODUCES" in text, "outputs block missing"
    assert 'mode not in ("execute", "inspect", "edit")' in text, "edit mode missing"
    assert "KISSPATH_PYTHON_ENV/bin/python" in text, "relocatable PROJECT_PY placeholder missing"
    assert "/mnt/disk1" not in text and "/home/server" not in text, "server-only path leaked"


def test_bundled_harness_matches_ported_server_copy_when_available():
    if not SERVER.is_file():
        import pytest
        pytest.skip("server copy not present on this machine")
    r = subprocess.run([sys.executable, str(REPO / "kiss" / "scripts" / "sync_harness.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout


def test_bundled_harness_imports_and_renders_all_three_modes(tmp_path):
    sys.path.insert(0, str(REPO / "kiss"))
    from kiss_cli import harness_runtime
    ki = tmp_path / "ki"; (ki / "tools").mkdir(parents=True)
    (ki / "tools" / "run.py").write_text("")
    (ki / "SKILL.md").write_text("# K\n> **MANDATORY EXECUTION POLICY**\n> run the real model\n\n")
    (ki / "dag.yaml").write_text("outputs:\n- var: q\n  validation_rank: 1\n  unit: m3/s\n")
    _pkg, impl = harness_runtime.load()
    for mode, marker in (("execute", "TOOLS (validated)"), ("inspect", "INSPECT mode"), ("edit", "EDIT mode")):
        text = impl.contract(str(ki), mode=mode)
        assert "[KI HARNESS v1]" in text and marker in text
    assert "rank 1: q [m3/s]" in impl.contract(str(ki))
