"""The desktop tool proxy under the flow (plan v3 B4/B5): schemas filtered by state, every
call re-checked, protected writes refused, receipts from run_ki_tool, stage never moved by
an agent report. Runs against a fake KI and the real bundled ki_tools_common.flow."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "kiss"))

from kiss_cli import api, flowgate, projectrun  # noqa: E402


@pytest.fixture(autouse=True)
def _keys(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("GEOFORGE_FLOW_KEYS", str(tmp_path_factory.mktemp("keys")))


def _ki(tmp_path, name="M"):
    root = tmp_path / "kis" / name
    (root / "tools").mkdir(parents=True)
    (root / "SKILL.md").write_text("# M\n> **MANDATORY EXECUTION POLICY**\n> run the real model\n\n")
    (root / "dag.yaml").write_text("outputs:\n- var: discharge\n  validation_rank: 1\n  unit: m3/s\n")
    (root / "tools" / "run.py").write_text(
        "import sys, pathlib\n"
        "out = pathlib.Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True)\n"
        "out.write_text('t,q\\n1,0.5\\n2,1.2\\n3,0.8\\n')\nprint('ran')\n")
    return SimpleNamespace(name=name, root=root)


def _cfg(project):
    return SimpleNamespace(root=project, python=sys.executable, roles={"binaries": project / "bin"})


def _plan(ki):
    return ({"schema_version": "1.0", "goal": "g", "selected_kis": [ki.name], "created_at": "t",
             "unresolved_questions": [],
             "steps": [{"id": "M:run", "ki": ki.name, "tool": str(ki.root / "tools" / "run.py"), "kind": "run",
                        "inputs": ["forcing"], "outputs": ["q"], "status": "planned"}],
             "scientific_choices": [{"id": "x", "kind": "other", "high_impact": False}]},
            {"schema_version": "1.0", "items": [{"id": "forcing", "required_by": [ki.name], "status": "resolved",
                                                 "acceptable_sources": ["cmfd_v1"], "chosen_source": "cmfd_v1",
                                                 "local_paths": [], "agent_resolvable": True, "needs_user": False}]})


def _session(tmp_path, ki, state_events=()):
    project = tmp_path / "project"; (project / "runs").mkdir(parents=True)
    fs = flowgate.FlowSession.open(project, {ki.name: ki.root}, python=sys.executable)
    for ev, evidence in state_events:
        fs.move(ev, evidence)
    return project, fs


def test_flow_loads_from_the_bundled_source():
    pkg = flowgate.load()
    assert pkg.__file__.startswith(str(REPO / "ki_tools_common"))


def test_planning_filters_schemas_and_refuses_execution(tmp_path):
    ki = _ki(tmp_path)
    project, fs = _session(tmp_path, ki, [("task_received", None), ("kis_resolved", {"selected_kis": ["M"]})])
    names = {t["name"] for t in api.tool_schemas(ki, project_mode=True, flow=fs)}
    assert "write_plan" in names and "run_ki_tool" not in names and "fetch_data" not in names
    with pytest.raises(api.ToolError, match="not allowed while the project is in PLANNING"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py"}, ki, _cfg(project), project_mode=True, flow=fs)
    with pytest.raises(api.ToolError):
        api.execute_tool("fetch_data", {"url": "https://x/y", "item_id": "forcing"}, ki, _cfg(project),
                         project_mode=True, flow=fs)
    # the planning turn may write ONLY the two plan files
    with pytest.raises(api.ToolError, match="not allowed while the project is in PLANNING"):
        api.execute_tool("write_project_file", {"path": "outputs/x.csv", "content": "1"}, ki, _cfg(project),
                         project_mode=True, flow=fs)


def test_write_plan_validates_then_writes(tmp_path):
    ki = _ki(tmp_path)
    project, fs = _session(tmp_path, ki, [("task_received", None), ("kis_resolved", {"selected_kis": ["M"]})])
    pj, inv = _plan(ki)
    bad = json.loads(json.dumps(pj)); bad["steps"][0]["tool"] = str(ki.root / "SKILL.md")
    out = api.execute_tool("write_plan", {"plan": bad, "data_inventory": inv}, ki, _cfg(project), project_mode=True, flow=fs)
    assert out.startswith("PLAN NOT WRITTEN") and not (project / "runs" / "plan.json").exists()
    out = api.execute_tool("write_plan", {"plan": pj, "data_inventory": inv}, ki, _cfg(project), project_mode=True, flow=fs)
    assert "Plan files written" in out and (project / "runs" / "plan.json").exists()


def test_protected_files_are_never_agent_writable(tmp_path):
    ki = _ki(tmp_path)
    project, fs = _session(tmp_path, ki, [("task_received", None), ("kis_resolved", {"selected_kis": ["M"]})])
    pj, inv = _plan(ki)
    fs.write_plan(pj, inv); fs.flow.approval.approve(project, by="auto"); fs.reload_artifacts()
    fs.move("plan_written", {"plan_valid": True}); fs.move("approved", {"approval": "OK"})
    fs.move("execution_started", {"setup_verified": True})
    for rel in ("runs/approval.json", "runs/flow-state.json", "runs/plan.json", "runs/anything.json"):
        with pytest.raises(api.ToolError):
            api.execute_tool("write_project_file", {"path": rel, "content": "{}"}, ki, _cfg(project),
                             project_mode=True, flow=fs)
    assert "wrote outputs/note.txt" in api.execute_tool(
        "write_project_file", {"path": "outputs/note.txt", "content": "x"}, ki, _cfg(project), project_mode=True, flow=fs)


def test_run_ki_tool_in_executing_writes_a_receipt_and_validates(tmp_path):
    ki = _ki(tmp_path)
    project, fs = _session(tmp_path, ki, [("task_received", None), ("kis_resolved", {"selected_kis": ["M"]})])
    pj, inv = _plan(ki)
    fs.write_plan(pj, inv); fs.flow.approval.approve(project, by="auto"); fs.reload_artifacts()
    fs.move("plan_written", {"plan_valid": True}); fs.move("approved", {"approval": "OK"})
    fs.move("execution_started", {"setup_verified": True})
    names = {t["name"] for t in api.tool_schemas(ki, project_mode=True, flow=fs)}
    assert "run_ki_tool" in names and "fetch_data" in names and "write_plan" not in names
    with pytest.raises(api.ToolError, match="plan_step_id is required"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["outputs/q.csv"]},
                         ki, _cfg(project), project_mode=True, flow=fs)
    out = api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["outputs/q.csv"],
                                           "plan_step_id": "M:run"}, ki, _cfg(project), project_mode=True, flow=fs)
    assert out.startswith("exit_code=0") and "[RECEIPT]" in out
    summary = json.loads(out.splitlines()[1].split("[RECEIPT] ", 1)[1])
    assert summary["validation"] == "passed" and "outputs/q.csv" in summary["outputs"]
    rec = json.loads(Path(summary["receipt"]).read_text())
    assert fs.flow.receipts.verify(project, rec) and rec["plan_step_id"] == "M:run" and rec["exit_code"] == 0
    ev = fs.evidence()
    assert ev["receipts_verified"] is True and ev["validation"] == "passed" and ev["steps_missing"] == []
    # a step id not in the plan is refused
    with pytest.raises(api.ToolError, match="not a step of the approved plan"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["outputs/z.csv"],
                                         "plan_step_id": "M:ghost"}, ki, _cfg(project), project_mode=True, flow=fs)


def test_run_ki_tool_refused_when_approval_drifts(tmp_path):
    ki = _ki(tmp_path)
    project, fs = _session(tmp_path, ki, [("task_received", None), ("kis_resolved", {"selected_kis": ["M"]})])
    pj, inv = _plan(ki)
    fs.write_plan(pj, inv); fs.flow.approval.approve(project, by="auto"); fs.reload_artifacts()
    fs.move("plan_written", {"plan_valid": True}); fs.move("approved", {"approval": "OK"})
    fs.move("execution_started", {"setup_verified": True})
    pj["goal"] = "changed"; fs.flow.plan.write_artifacts(project, pj, inv)
    with pytest.raises(api.ToolError, match="no valid approval"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["outputs/q.csv"],
                                         "plan_step_id": "M:run"}, ki, _cfg(project), project_mode=True, flow=fs)


def test_progress_report_cannot_move_the_stage_once_flow_owned(tmp_path):
    ki = _ki(tmp_path)
    project, fs = _session(tmp_path, ki, [("task_received", None), ("kis_resolved", {"selected_kis": ["M"]})])
    projectrun.set_stage(project, "preparing", "planning")
    out = api.execute_tool("report_project_progress", {"stage": "results", "status": "complete", "summary": "done!"},
                           ki, _cfg(project), project_mode=True, flow=fs)
    state = projectrun.load(project)
    assert state["stage"] == "preparing" and state["summary"] == "done!" and "tracked by GeoForge" in out
    # a native agent's status file cannot move it either
    (project / "runs" / "project-agent-status.json").write_text(json.dumps({"stage": "results", "status": "complete"}))
    assert projectrun.load(project)["stage"] == "preparing"
    with pytest.raises(ValueError):
        projectrun.set_stage(project, "results", source="agent")


def test_multi_ki_run_ki_tool_selects_by_name(tmp_path):
    a, b = _ki(tmp_path, "A"), _ki(tmp_path, "B")
    project = tmp_path / "project"; (project / "runs").mkdir(parents=True)
    fs = flowgate.FlowSession.open(project, {"A": a.root, "B": b.root}, python=sys.executable)
    fs.move("task_received"); fs.move("kis_resolved", {"selected_kis": ["A", "B"]})
    pj, inv = _plan(a); pj["selected_kis"] = ["A", "B"]
    pj["steps"] = [{"id": "A:run", "ki": "A", "tool": str(a.root / "tools" / "run.py"), "kind": "run", "inputs": ["forcing"], "outputs": [], "status": "planned"},
                   {"id": "B:run", "ki": "B", "tool": str(b.root / "tools" / "run.py"), "kind": "run", "inputs": ["forcing"], "outputs": [], "status": "planned"}]
    inv["items"][0]["required_by"] = ["A", "B"]
    assert fs.write_plan(pj, inv) == []
    fs.flow.approval.approve(project, by="auto"); fs.reload_artifacts()
    fs.move("plan_written", {"plan_valid": True}); fs.move("approved", {"approval": "OK"}); fs.move("execution_started", {"setup_verified": True})
    out = api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["outputs/b.csv"], "ki": "B",
                                           "plan_step_id": "B:run"}, a, _cfg(project), project_mode=True, flow=fs)
    assert out.startswith("exit_code=0")
    with pytest.raises(api.ToolError, match="not one of the selected KIs"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "ki": "C", "plan_step_id": "A:run"},
                         a, _cfg(project), project_mode=True, flow=fs)


def test_read_and_list_ki_files_reach_every_selected_ki(tmp_path):
    a, b = _ki(tmp_path, "A"), _ki(tmp_path, "B")
    (b.root / "docs").mkdir(); (b.root / "docs" / "note.md").write_text("B doc")
    project = tmp_path / "project"; (project / "runs").mkdir(parents=True)
    fs = flowgate.FlowSession.open(project, {"A": a.root, "B": b.root}, python=sys.executable)
    fs.move("task_received"); fs.move("kis_resolved", {"selected_kis": ["A", "B"]})
    assert api.execute_tool("read_ki_file", {"path": "docs/note.md", "ki": "B"}, a, _cfg(project),
                            project_mode=True, flow=fs) == "B doc"
    assert "docs/note.md" in api.execute_tool("list_ki_files", {"ki": "B"}, a, _cfg(project), project_mode=True, flow=fs)
    with pytest.raises(api.ToolError, match="not one of the selected KIs"):
        api.execute_tool("read_ki_file", {"path": "SKILL.md", "ki": "C"}, a, _cfg(project), project_mode=True, flow=fs)
    with pytest.raises(api.ToolError, match="escapes"):
        api.execute_tool("read_ki_file", {"path": "../A/SKILL.md", "ki": "B"}, a, _cfg(project), project_mode=True, flow=fs)


def test_progress_prompt_has_no_stage_under_the_flow(tmp_path):
    project = tmp_path / "project"; (project / "runs").mkdir(parents=True)
    assert '"stage":' in projectrun.prompt_block(project)
    fs = flowgate.FlowSession.open(project, {}); fs.move("task_received")
    assert '"stage":' not in projectrun.prompt_block(project) and "GEOFORGE TRACKS THE STAGE" in projectrun.prompt_block(project)
