"""`kiss run-tool` / `kiss fetch`: the only execution surface a CLI agent gets in EXECUTING."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "kiss"))

from kiss_cli import cli, flowrun, paths  # noqa: E402


@pytest.fixture(autouse=True)
def _keys(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("GEOFORGE_FLOW_KEYS", str(tmp_path_factory.mktemp("keys")))


def _project_with_ki(tmp_path):
    project = tmp_path / "project"; (project / "runs").mkdir(parents=True)
    root = project / "models" / "M" / "ki"; (root / "tools").mkdir(parents=True)
    (root / "SKILL.md").write_text("# M\n> **MANDATORY EXECUTION POLICY**\n> run it\n\n")
    (root / "dag.yaml").write_text("outputs:\n- var: discharge\n  validation_rank: 1\n  unit: m3/s\n"
                                   "processes:\n  modules:\n  - id: run\n")
    (root / "tools" / "run.py").write_text(
        "import sys, pathlib\nout = pathlib.Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True)\n"
        "out.write_text('t,q\\n1,0.5\\n2,1.2\\n')\n")
    cfg = paths.KissConfig.default(project)
    try:
        cfg.python = Path(sys.executable)
    except Exception:
        pass
    (project / paths.CONFIG_NAME).write_text(cfg.dumps(), encoding="utf-8")
    return project, SimpleNamespace(name="M", root=root)


def _approve(project, ki):
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = flowrun.turn(project, [ki], SimpleNamespace(root=project, python=sys.executable, roles={}),
                     "cli", "claude", None, "run M for 2003")
    pj, inv = t.session.flow.plan.read_artifacts(project)
    for st in pj["steps"]:
        st["tool"] = str(ki.root / "tools" / "run.py"); st["kind"] = "run"
    for it in inv["items"]:
        it["status"] = "resolved"; it["needs_user"] = False
    assert t.session.write_plan(pj, inv) == []
    res = flowrun.after(project, t, "planned", setup_ok=True)
    assert res.continue_now
    return pj["steps"][0]["id"]


def test_run_tool_refused_before_approval_and_writes_receipt_after(tmp_path, capsys, monkeypatch):
    project, ki = _project_with_ki(tmp_path)
    monkeypatch.chdir(project)
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)          # PLANNING
    rc = cli.main(["run-tool", "--step", "M:run", "M", "tools/run.py", "--", "outputs/q.csv"])
    assert rc == 3 and "not EXECUTING" in capsys.readouterr().err
    step = _approve(project, ki)                                                 # EXECUTING
    rc = cli.main(["run-tool", "--step", step, "M", "tools/run.py", "--", "outputs/q.csv"])
    out = capsys.readouterr().out
    assert rc == 0 and "[RECEIPT]" in out
    summary = json.loads(out.split("[RECEIPT] ", 1)[1].strip().splitlines()[0])
    rec = json.loads(Path(summary["receipt"]).read_text())
    assert rec["plan_step_id"] == step and rec["exit_code"] == 0 and summary["validation"] == "passed"
    # a tool outside tools/ or a step not in the plan is refused
    assert cli.main(["run-tool", "--step", step, "M", "SKILL.md"]) == 3
    assert cli.main(["run-tool", "--step", "M:ghost", "M", "tools/run.py", "--", "outputs/z.csv"]) == 3


def test_fetch_refused_outside_executing(tmp_path, capsys, monkeypatch):
    project, ki = _project_with_ki(tmp_path)
    monkeypatch.chdir(project)
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    rc = cli.main(["fetch", "https://example.invalid/x.csv", "--item", "forcing"])
    assert rc == 3 and "not EXECUTING" in capsys.readouterr().err


def test_wrapper_commands_are_the_app_itself():
    w = flowrun.wrapper_commands()
    assert w["run_tool"].endswith("run-tool") and w["fetch"].endswith("fetch")
    assert sys.executable in w["run_tool"]
