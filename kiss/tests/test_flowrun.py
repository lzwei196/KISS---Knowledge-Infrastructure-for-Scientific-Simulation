"""flowrun: the desktop turn under the flow — resolution, planning turn, approval card,
execution turn, evidence. No agent is spawned; the API provider path is exercised through
the same objects gui.py uses (fake catalogue, fake KI, fake cfg)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "kiss"))

from kiss_cli import api, flowgate, flowrun, projectrun, setup as setup_flow  # noqa: E402


@pytest.fixture(autouse=True)
def _keys(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("GEOFORGE_FLOW_KEYS", str(tmp_path_factory.mktemp("keys")))


def _ki(tmp_path, name):
    root = tmp_path / "kis" / name
    (root / "tools").mkdir(parents=True)
    (root / "SKILL.md").write_text(f"# {name}\n> **MANDATORY EXECUTION POLICY**\n> run the real model\n\n")
    (root / "dag.yaml").write_text("outputs:\n- var: discharge\n  validation_rank: 1\n  unit: m3/s\n"
                                   "processes:\n  modules:\n  - id: run\n    inputs: []\n    outputs: [discharge]\n")
    (root / "tools" / "run.py").write_text(
        "import sys, pathlib\nout = pathlib.Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True)\n"
        "out.write_text('t,q\\n1,0.5\\n2,1.2\\n3,0.8\\n')\n")
    return SimpleNamespace(name=name, root=root)


def _project(tmp_path):
    p = tmp_path / "project"; (p / "runs").mkdir(parents=True)
    return p


def _cfg(project):
    return SimpleNamespace(root=project, python=sys.executable, roles={"binaries": project / "bin"})


def test_pre_ungated_for_small_talk_and_gated_for_science(tmp_path):
    project = _project(tmp_path); cat = [_ki(tmp_path, "VIC"), _ki(tmp_path, "CaMa_Flood")]
    r = flowrun.pre(project, "hello, what can you do?", [], cat, None, None)
    assert r.gated is False and not (project / "runs" / "flow-state.json").exists()
    r = flowrun.pre(project, "run VIC–CaMa flood at Bengbu 2003-2005", [], cat, None, None,
                    couplings_dir=None)
    assert r.gated and r.names == ["VIC", "CaMa_Flood"] and r.message is None
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "PLANNING" and st["selected_kis"] == ["VIC", "CaMa_Flood"]
    assert projectrun.load(project)["selected_kis"] == ["VIC", "CaMa_Flood"]


def test_pre_asks_about_unknown_model_instead_of_guessing(tmp_path):
    project = _project(tmp_path); cat = [_ki(tmp_path, "VIC")]
    r = flowrun.pre(project, "run VIC-CaMa flood", [], cat, None, None)
    assert r.message and "CaMa" in r.message and r.names == ["VIC"]
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "WAITING_FOR_USER"
    # the user answers with a real model → planning
    r = flowrun.pre(project, "just VIC then", ["VIC"], cat, None, None)
    assert r.names == ["VIC"] and r.message is None
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "PLANNING"


def _drive_planning(tmp_path, ki, project, with_choice=False):
    resolved = [ki]
    t = flowrun.turn(project, resolved, _cfg(project), "api", "deepseek", None,
                     "run M at 32.9, 117.4 for 2003-2004")
    assert t is not None and t.execute is False and "INSPECT mode" in t.extra_prompt
    assert "PLAN DRAFT" in t.extra_prompt and (project / "runs" / "plan.json").exists()
    # the agent "corrects" the draft: fill the tool, keep everything resolved
    pj, inv = t.session.flow.plan.read_artifacts(project)
    for st in pj["steps"]:
        st["tool"] = str(ki.root / "tools" / "run.py"); st["kind"] = "run"
    if with_choice:
        pj["scientific_choices"] = [{"id": "f", "kind": "forcing_source", "options": ["cmfd_v1", "mswx_v1"],
                                     "picked": "cmfd_v1", "high_impact": True}]
    for it in inv["items"]:
        it["status"] = "resolved"; it["needs_user"] = False
    errs = t.session.write_plan(pj, inv)
    assert errs == [], errs
    return t


def test_planning_turn_then_auto_approval_then_execution_and_evidence(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M at 32.9, 117.4 for 2003-2004", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project)
    res = flowrun.after(project, t, "I wrote the plan.", setup_ok=True)
    assert res.request is None and res.continue_now is True
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "EXECUTING" and (project / "runs" / "approval.json").exists()
    assert json.loads((project / "runs" / "approval.json").read_text())["approved_by"] == "auto"
    # execution turn: run contract, receipts required
    t2 = flowrun.turn(project, [ki], _cfg(project), "api", "deepseek", None, "go")
    assert t2.execute is True and "STAGE GROUNDING" in t2.extra_prompt and "TOOLS (validated)" in t2.extra_prompt
    step = t2.session.plan["steps"][0]["id"]
    out = api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["outputs/q.csv"],
                                           "plan_step_id": step}, ki, _cfg(project), project_mode=True,
                           flow=t2.session)
    assert "[RECEIPT]" in out
    res = flowrun.after(project, t2, "done", setup_ok=True)
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "COMPLETED", st
    ev = json.loads((project / "runs" / "evidence.json").read_text())
    assert ev["receipts_verified"] and ev["validation"] == "passed"
    assert projectrun.load(project)["stage"] == "results"


def test_high_impact_choice_shows_the_approval_card_and_click_approves(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project, with_choice=True)
    res = flowrun.after(project, t, "plan written", setup_ok=True)
    assert res.request and res.request["id"].startswith(flowrun.APPROVAL_REQUEST_ID_PREFIX)
    assert {o["id"] for o in res.request["options"]} == {"approve", "modify"}
    assert "You decide" in res.request["message"] and "forcing_source" in res.request["message"]
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "WAITING_FOR_USER"
    assert projectrun.load(project)["status"] == "waiting_for_user"
    pending = setup_flow.request(project)
    assert pending and pending["id"] == res.request["id"]
    # the user clicks approve
    r = flowrun.pre(project, "Approved. Start the execution.", ["M"], [ki],
                    {"request_id": pending["id"], "option_id": "approve", "note": "use cmfd"}, pending,
                    note="use cmfd", setup_ok=True)
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "EXECUTING" and r.message is None
    a = json.loads((project / "runs" / "approval.json").read_text())
    assert a["approved_by"] == "user" and a["decisions"] == {"note": "use cmfd"}
    assert setup_flow.request(project) is None


def test_modify_click_goes_back_to_planning_with_the_note(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project, with_choice=True)
    res = flowrun.after(project, t, "plan written", setup_ok=True)
    pending = setup_flow.request(project)
    r = flowrun.pre(project, "Please revise the plan.", ["M"], [ki],
                    {"request_id": pending["id"], "option_id": "modify", "note": "use MSWX"}, pending, note="use MSWX")
    assert r.replan_reason == "use MSWX"
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "PLANNING"
    t = flowrun.turn(project, [ki], _cfg(project), "api", "deepseek", None, "revise", replan_reason="use MSWX")
    assert "[RE-PLAN]" in t.extra_prompt and "use MSWX" in t.extra_prompt


def test_approval_without_verified_software_goes_to_setup(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project)
    res = flowrun.after(project, t, "plan written", setup_ok=False)
    assert res.continue_now is False
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "SETUP_REQUIRED"
    st = flowrun.setup_turn(project, [ki], _cfg(project), "cli", "claude")
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "SETUP_RUNNING"
    flowrun.setup_verified(project, [ki], _cfg(project))
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "APPROVED"


def test_executing_turn_detects_drift_and_replan_marker(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project)
    flowrun.after(project, t, "plan written", setup_ok=True)
    # the agent says it needs another model → re-plan
    t2 = flowrun.turn(project, [ki], _cfg(project), "api", "deepseek", None, "go")
    flowrun.after(project, t2, "I cannot do this: REPLAN_REQUIRED: routing needs CaMa_Flood", setup_ok=True)
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "REPLAN_REQUIRED"
    assert not (project / "runs" / "approval.json").exists()


def test_cli_policy_and_worktree_for_codex(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    (project / "outputs").mkdir(); (project / "outputs" / "old.csv").write_text("1")
    t = flowrun.turn(project, [ki], _cfg(project), "cli", "codex", None, "run M for 2003")
    assert t.planning_worktree is not None and t.planning_worktree.is_dir()
    assert not (t.planning_worktree / "outputs").exists()          # outputs never copied
    assert (t.planning_worktree / "runs" / "plan.json").exists()
    assert t.policy.enforcement.value == "approximate" and t.policy.planning_worktree
    tc = flowrun.turn(project, [ki], _cfg(project), "cli", "claude", None, "run M for 2003")
    assert tc.planning_worktree is None and tc.policy.argv_delta[0] == "--allowedTools"
    assert "--dangerously-skip-permissions" in tc.policy.drop_flags
