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
    # codex R2 #2: verification resumes straight into EXECUTING (APPROVED is passed through)
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "EXECUTING"


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


def test_project_view_labels_unvalidated_artifacts_under_the_flow(tmp_path):
    from kiss_cli import projectview
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    (project / "artifacts").mkdir()
    (project / "artifacts" / "handmade.svg").write_text("<svg/>")
    # no flow yet: no labels
    assert "evidence" not in projectview._automatic(project)["panels"][0]
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    view = projectview._automatic(project)
    assert view["panels"][0]["evidence"] == "unvalidated" and "unvalidated" in view["panels"][0]["title"]
    # a verified run output is labelled verified
    t = _drive_planning(tmp_path, ki, project)
    flowrun.after(project, t, "planned", setup_ok=True)
    t2 = flowrun.turn(project, [ki], _cfg(project), "api", "deepseek", None, "go")
    step = t2.session.plan["steps"][0]["id"]
    api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "arguments": ["artifacts/q.csv"],
                                     "plan_step_id": step}, ki, _cfg(project), project_mode=True, flow=t2.session)
    view = projectview._automatic(project)
    by = {p["path"]: p["evidence"] for p in view["panels"]}
    assert by["artifacts/q.csv"] == "verified" and by["artifacts/handmade.svg"] == "unvalidated"


def test_auto_turn_is_read_only_and_refuses_ungateable_providers(tmp_path):
    project = _project(tmp_path)
    flowrun.pre(project, "simulate the flood at Bengbu", [], [], None, None)   # nothing resolved
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "RESOLVING_KIS"
    t = flowrun.auto_turn(project, "api", "deepseek")
    assert "run_ki_tool" not in t.session.api_tools() and "write_plan" not in t.session.api_tools()
    assert "report_project_progress" in t.session.api_tools()
    tc = flowrun.auto_turn(project, "cli", "claude")
    assert tc.policy.argv_delta[0] == "--allowedTools" and "Write(" not in tc.policy.argv_delta[1]
    assert not tc.planning_worktree and not tc.policy.planning_worktree
    with pytest.raises(Exception, match="cannot be held to the planning gate"):
        flowrun.auto_turn(project, "cli", "gemini")


def test_setup_is_deferred_until_approval(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    assert flowrun.setup_allowed(project)                        # no flow yet: old behaviour
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    assert not flowrun.setup_allowed(project)                    # PLANNING: no compile grants
    t = _drive_planning(tmp_path, ki, project)
    flowrun.after(project, t, "planned", setup_ok=False)          # auto-approved, software missing
    assert flowrun.setup_allowed(project)                        # SETUP_REQUIRED


def test_wrapper_commands_have_no_spaces_in_the_executable_path(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "GeoForge Desktop"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    w = flowrun.wrapper_commands()
    base = w["run_tool"].rsplit(" run-tool", 1)[0]
    assert " " not in base or base.startswith("'"), w
    if " " not in base:
        assert Path(base).is_file() and "GeoForge Desktop" in Path(base).read_text()


def test_provider_refusal_for_gemini_and_qwen():
    assert flowrun.provider_refusal("cli", "gemini") and flowrun.provider_refusal("cli", "qwen")
    assert flowrun.provider_refusal("cli", "claude") is None and flowrun.provider_refusal("api", "deepseek") is None


def test_setup_verified_resumes_into_executing_and_continues(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project)
    flowrun.after(project, t, "planned", setup_ok=False)                 # SETUP_REQUIRED
    st = flowrun.setup_turn(project, [ki], _cfg(project), "cli", "claude")
    flowrun.setup_verified(project, [ki], _cfg(project))
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "EXECUTING"
    assert flowrun.after(project, st, "installed", setup_ok=True).continue_now is True


def test_auto_choice_is_promoted_into_the_flow(tmp_path):
    project = _project(tmp_path); cat = [_ki(tmp_path, "VIC"), _ki(tmp_path, "DSSAT")]
    flowrun.pre(project, "simulate the flood at Bengbu", [], cat, None, None)   # RESOLVING_KIS
    projectrun.report(project, {"status": "working", "summary": "picked", "selected_kis": ["VIC", "Nope"]})
    assert flowrun.promote_auto_choice(project, cat) == ["VIC"]
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "PLANNING" and st["selected_kis"] == ["VIC"]
    assert flowrun.promote_auto_choice(project, cat) == ["VIC"]           # idempotent


def test_run_ki_tool_checks_step_ki_and_tool_before_running(tmp_path):
    project = _project(tmp_path); a, b = _ki(tmp_path, "A"), _ki(tmp_path, "B")
    (a.root / "tools" / "other.py").write_text("print('x')")
    flowrun.pre(project, "run A and B for 2003", ["A", "B"], [a, b], None, None)
    t = flowrun.turn(project, [a, b], _cfg(project), "api", "deepseek", None, "run A and B")
    pj, inv = t.session.flow.plan.read_artifacts(project)
    pj["steps"] = [{"id": "A:run", "ki": "A", "tool": str(a.root / "tools" / "run.py"), "kind": "run",
                    "inputs": [], "outputs": [], "status": "planned"}]
    for it in inv["items"]:
        it["status"] = "resolved"; it["needs_user"] = False
    assert t.session.write_plan(pj, inv) == []
    flowrun.after(project, t, "planned", setup_ok=True)
    t2 = flowrun.turn(project, [a, b], _cfg(project), "api", "deepseek", None, "go")
    with pytest.raises(api.ToolError, match="belongs to KI 'A'"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/run.py", "ki": "B", "plan_step_id": "A:run",
                                         "arguments": ["outputs/b.csv"]}, a, _cfg(project), project_mode=True, flow=t2.session)
    with pytest.raises(api.ToolError, match="approved for tool"):
        api.execute_tool("run_ki_tool", {"tool_path": "tools/other.py", "plan_step_id": "A:run",
                                         "arguments": ["outputs/o.csv"]}, a, _cfg(project), project_mode=True, flow=t2.session)
    assert not (project / "outputs").exists()                              # nothing ran
    names = {t["name"]: t for t in api.tool_schemas(a, project_mode=True, flow=t2.session)}
    assert "stage" not in names["report_project_progress"]["input_schema"]["properties"]


def test_setup_turn_keeps_the_desktop_setup_grants_on_cli(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project)
    flowrun.after(project, t, "planned", setup_ok=False)                  # SETUP_REQUIRED
    st = flowrun.setup_turn(project, [ki], _cfg(project), "cli", "claude")
    assert st.kind == "setup" and flowrun.policy_for_cli(st, "claude", None) is None


def test_launcher_is_rewritten_when_the_executable_changes(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "executable", str(tmp_path / "GeoForge Desktop v1"))
    w1 = flowrun.wrapper_commands()["run_tool"].rsplit(" run-tool", 1)[0]
    monkeypatch.setattr(sys, "executable", str(tmp_path / "GeoForge Desktop v2"))
    w2 = flowrun.wrapper_commands()["run_tool"].rsplit(" run-tool", 1)[0]
    assert w1 == w2 and "v2" in Path(w2).read_text() and "/tmp/" not in w2
