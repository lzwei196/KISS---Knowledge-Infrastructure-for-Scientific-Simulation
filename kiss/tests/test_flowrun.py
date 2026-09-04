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

from kiss_cli import api, flowgate, flowrun, gui, projectrun, setup as setup_flow  # noqa: E402


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
    assert r.gated and r.names == [] and r.message is None
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "RESOLVING_KIS"
    assert projectrun.load(project)["stage"] == "understanding"
    reply = ('<!-- GEOFORGE_INTAKE {"selected_kis":["VIC","CaMa_Flood"],'
             '"ready_for_planning":true,"understanding":"VIC-CaMa flood at Bengbu",'
             '"study_area":"Bengbu","period":"2003-2005","process":"rainfall-runoff and routing",'
             '"scenario":"baseline","requested_outputs":["discharge"],"missing":[]} -->')
    assert flowrun.promote_auto_choice(project, cat, reply) == ["VIC", "CaMa_Flood"]
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "PLANNING" and st["selected_kis"] == ["VIC", "CaMa_Flood"]
    assert projectrun.load(project)["selected_kis"] == ["VIC", "CaMa_Flood"]


def test_unknown_model_is_clarified_by_agent_intake_not_host_regex(tmp_path):
    project = _project(tmp_path); cat = [_ki(tmp_path, "VIC")]
    r = flowrun.pre(project, "run VIC-CaMa flood", [], cat, None, None)
    assert r.message is None and r.names == []
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "RESOLVING_KIS"
    reply = ('I can use VIC, but CaMa is not in this library. Should I continue with VIC only? '
             '<!-- GEOFORGE_INTAKE {"selected_kis":["VIC"],"ready_for_planning":false,'
             '"understanding":"VIC-CaMa flood study","study_area":"","period":"",'
             '"process":"rainfall-runoff and routing","scenario":"",'
             '"requested_outputs":["discharge"],"missing":["whether VIC-only is acceptable"]} -->')
    assert flowrun.promote_auto_choice(project, cat, reply) == []
    assert json.loads((project / "runs" / "flow-state.json").read_text())["state"] == "RESOLVING_KIS"


def test_private_intake_marker_is_removed_from_saved_chat_text():
    reply = ('目标理解\n\n请告诉我具体流域。\n'
             '<!-- GEOFORGE_INTAKE {"selected_kis":["CRHM"],'
             '"ready_for_planning":false,"missing":["具体流域"]} -->')

    visible = flowrun.strip_intake_markers(reply)

    assert visible.strip() == "目标理解\n\n请告诉我具体流域。"
    assert "GEOFORGE_INTAKE" not in visible


def test_pre_accepts_crhm_embedded_in_chinese_scientific_request(tmp_path):
    project = _project(tmp_path)
    cat = [_ki(tmp_path, "CRHM")]
    r = flowrun.pre(project, "我想要用CRHM模拟中国高寒区融雪径流", [], cat,
                    None, None)
    assert r.gated and r.names == [] and r.message is None
    st = json.loads((project / "runs" / "flow-state.json").read_text())
    assert st["state"] == "RESOLVING_KIS"
    reply = ('我理解为使用 CRHM 研究中国高寒区融雪径流。请给出模拟时段和具体流域。 '
             '<!-- GEOFORGE_INTAKE {"selected_kis":["CRHM"],"ready_for_planning":false,'
             '"understanding":"使用 CRHM 模拟中国高寒区融雪径流",'
             '"study_area":"中国高寒区（具体流域待定）","period":"",'
             '"process":"积雪积累、融雪与径流形成","scenario":"",'
             '"requested_outputs":["融雪量","径流过程"],'
             '"missing":["具体流域或空间范围","模拟时段"]} -->')
    assert flowrun.promote_auto_choice(project, cat, reply) == []
    intake = projectrun.load(project)["intake"]
    assert intake["process"] == "积雪积累、融雪与径流形成" and not intake["ready_for_planning"]


def test_pinned_ki_does_not_treat_dataset_acronyms_as_unknown_models(tmp_path):
    project = _project(tmp_path)
    cat = [_ki(tmp_path, "AquaCrop")]

    result = flowrun.pre(
        project,
        "Run AquaCrop with NASA POWER API weather, DEM and CMFD comparison",
        ["AquaCrop"], cat, None, None,
    )

    assert result.gated and result.names == ["AquaCrop"]
    state = json.loads((project / "runs" / "flow-state.json").read_text())
    assert state["state"] == "PLANNING"
    assert state["selected_kis"] == ["AquaCrop"]


def test_pinned_ki_is_not_expanded_by_negated_models_or_alias_collisions(tmp_path):
    project = _project(tmp_path)
    cat = [_ki(tmp_path, "VIC"), _ki(tmp_path, "CaMa_Flood"),
           _ki(tmp_path, "Cell2Fire")]

    result = flowrun.pre(
        project,
        "Run a single grid cell with VIC; do not invoke CaMa-Flood",
        ["VIC"], cat, None, None,
    )

    assert result.gated and result.names == ["VIC"]
    state = json.loads((project / "runs" / "flow-state.json").read_text())
    assert state["state"] == "PLANNING"
    assert state["selected_kis"] == ["VIC"]


def test_agent_intake_can_resolve_chinese_crhm_task_into_semantic_plan(tmp_path):
    project = _project(tmp_path)
    cat = [_ki(tmp_path, "CRHM")]
    goal = "我想要用CRHM模拟中国高寒区融雪径流"
    r = flowrun.pre(project, goal, [], cat, None, None)
    assert r.names == [] and r.message is None
    reply = ('<!-- GEOFORGE_INTAKE {"selected_kis":["CRHM"],"ready_for_planning":true,'
             '"understanding":"使用 CRHM 模拟祁连山流域 2001-2010 年融雪径流",'
             '"study_area":"中国祁连山某流域","period":"2001-2010",'
             '"process":"积雪积累、能量平衡融雪与径流形成","scenario":"历史基准",'
             '"requested_outputs":["SWE","融雪量","出口径流"],"missing":[]} -->')
    assert flowrun.promote_auto_choice(project, cat, reply) == ["CRHM"]
    t = flowrun.turn(project, cat, _cfg(project), "api", "deepseek", None, goal)
    pj, _ = t.session.flow.plan.read_artifacts(project)
    assert pj["intent"]["study_area"] == "中国祁连山某流域"
    assert pj["intent"]["period"] == "2001-2010"
    assert pj["intent"]["process"] == "积雪积累、能量平衡融雪与径流形成"
    assert pj["intent"]["requested_outputs"] == ["SWE", "融雪量", "出口径流"]


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


def test_gated_auto_api_receives_only_the_task_intake_contract(monkeypatch, tmp_path):
    """The API path used to drop the appended intake prompt and retain conflicting
    execution rules.  Exercise the actual Handler seam so this cannot regress silently."""
    project = _project(tmp_path)
    ki = _ki(tmp_path, "CRHM")
    ki.meta = {"reference": "Cold Regions Hydrological Model"}

    class Catalogue(list):
        models_dir = tmp_path / "kis"

    catalog = Catalogue([ki])
    pre = flowrun.pre(project, "我想要用CRHM模拟中国高寒区融雪径流", [], catalog,
                      None, None)
    handler = object.__new__(gui.Handler)
    handler.catalog = catalog
    handler.workroot = tmp_path
    handler._status_for = lambda _ki: {"label": "Verified", "can_run": True}
    captured = {}

    def fake_run(_provider, _ki, _cfg, system, task, **kwargs):
        captured.update(system=system, task=task, flow=kwargs.get("flow"))
        yield "请提供具体流域和模拟时段。"

    monkeypatch.setattr(api, "run", fake_run)
    pieces = []
    handler._chat_auto(
        "api:deepseek", "USER: 我想要用CRHM模拟中国高寒区融雪径流",
        lambda piece: pieces.append(piece) or True, project,
        bare_task="我想要用CRHM模拟中国高寒区融雪径流", flow_pre=pre,
    )
    assert captured["task"] == "我想要用CRHM模拟中国高寒区融雪径流"
    assert "[TASK UNDERSTANDING — NO EXECUTION]" in captured["system"]
    assert "The user's message is a scientific goal" in captured["system"]
    assert "[AGENT-FIRST PROJECT PREPARATION]" not in captured["system"]
    assert "[KI CHOICE IS YOURS]" not in captured["system"]
    assert captured["flow"] is not None


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
    projectrun.report(project, {"status": "working", "summary": "picked", "selected_kis": ["VIC", "Nope"],
                                "intake": {"ready_for_planning": True,
                                           "understanding": "VIC flood simulation at Bengbu",
                                           "study_area": "Bengbu", "period": "2003-2005",
                                           "process": "rainfall-runoff", "scenario": "baseline",
                                           "requested_outputs": ["discharge"], "missing": []}})
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
    assert w1 == w2 and "v2" in Path(w2).read_text()
    assert Path(w2).is_relative_to(tmp_path / "home")          # user-owned dir, never $TMPDIR


@pytest.mark.parametrize("provider", ["codex", "kimi", "claude"])
def test_untouched_draft_never_becomes_an_approval(tmp_path, provider):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = flowrun.turn(project, [ki], _cfg(project), "cli", provider, None, "run M for 2003")
    result = flowrun.after(project, t, "could not save")
    assert result.message and not result.request and not result.continue_now
    assert t.session.state.value == "PLANNING"
    assert not (project / "runs/approval.json").exists()


def test_failed_provider_with_saved_files_cannot_offer_approval(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project, with_choice=True)
    t.provider_succeeded = False
    result = flowrun.after(project, t, "CLI exited 2")
    assert "failed" in result.message and result.request is None
    assert t.session.state.value == "PLANNING"


@pytest.mark.parametrize("changed", [True, False])
def test_worktree_handoff_preserves_reviewed_plan_even_if_unchanged(tmp_path, changed):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = flowrun.turn(project, [ki], _cfg(project), "cli", "kimi", None, "run M for 2003")
    wt = t.planning_worktree
    assert str(wt / "runs/plan.json") in t.extra_prompt
    pj, inv = t.session.flow.plan.read_artifacts(wt)
    if changed:
        pj["goal"] = "Reviewed by the agent"
    t.session.flow.plan.write_artifacts(wt, pj, inv)
    result = flowrun.after(project, t, "saved both")
    assert result.request and result.message == ""
    assert json.loads((project / "runs/plan.json").read_text()) == pj
    assert wt.is_dir()  # preserve submitted evidence


def test_concurrent_original_edit_is_not_overwritten(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = flowrun.turn(project, [ki], _cfg(project), "cli", "codex", None, "run M for 2003")
    pj, inv = t.session.flow.plan.read_artifacts(t.planning_worktree)
    t.session.flow.plan.write_artifacts(t.planning_worktree, pj, inv)
    pj["goal"] = "user concurrent edit"
    t.session.flow.plan.write_artifacts(project, pj, inv)
    result = flowrun.after(project, t, "saved")
    assert "original plan changed" in result.message and not result.request
    assert json.loads((project / "runs/plan.json").read_text())["goal"] == "user concurrent edit"


def test_review_card_cannot_approve_a_changed_inventory(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project, with_choice=True)
    result = flowrun.after(project, t, "saved")
    pending = setup_flow.request(project)
    (project / "runs/data-inventory.json").write_text('{"schema_version":"1.0","items":[],"changed":true}')
    pre = flowrun.pre(project, "approve", ["M"], [ki],
                      {"request_id": pending["id"], "option_id": "approve"}, pending)
    assert pre.replan_reason and not (project / "runs/approval.json").exists()


@pytest.mark.parametrize("text", ["准备蚌埠站 VIC-CaMa，输入数据", "Prepare VIC-CaMa, input data"])
def test_preparation_intent_and_punctuation_select_both_models(tmp_path, text):
    project = _project(tmp_path); cat = [_ki(tmp_path, "VIC"), _ki(tmp_path, "CaMa_Flood")]
    pre = flowrun.pre(project, text, ["VIC"], cat, None, None)
    assert pre.gated and pre.names == ["VIC", "CaMa_Flood"]


def test_argv_replacement_removes_variadic_grants_and_equals_flags():
    from kiss_cli import providers
    args = ["--allowedTools", "Read(//x/**)", "Write(//x/**)", "--sandbox=workspace-write",
            "--sandbox", "danger-full-access", "--permission-mode", "bypassPermissions", "--verbose"]
    assert providers._strip_flags(args, ("--allowedTools", "--sandbox", "--permission-mode")) == ["--verbose"]


def test_claude_planning_paths_and_tool_surface(tmp_path):
    p = flowrun._flow().policy
    project = tmp_path / "带 空格的项目"; ki = _ki(tmp_path, "M")
    policy = p.for_state(flowrun._flow().states.State.PLANNING, "claude", project, {"M": ki.root})
    grants = policy.argv_delta[1]
    assert f"Write(/{project}/runs/plan.json)" in grants
    assert "Bash(" not in grants and "bypassPermissions" not in policy.argv_delta
    assert "dontAsk" in policy.argv_delta
    assert p.claude_path(r"C:\Users\User Name\项目") == "//c/Users/User Name/项目"


def test_declared_legacy_stage_tool_is_not_arbitrary_code(tmp_path):
    from ki_tools_common.flow.tools import is_ki_tool
    ki = _ki(tmp_path, "M")
    stage = ki.root / "s1_grid"; stage.mkdir()
    tool = stage / "prepare.py"; tool.write_text("pass")
    assert not is_ki_tool(ki.root, tool)
    (ki.root / "SKILL.md").write_text("Run `s1_grid/prepare.py`.")
    assert is_ki_tool(ki.root, tool)
    outside = tmp_path / "outside.py"; outside.write_text("pass")
    (ki.root / "tools/escape.py").symlink_to(outside)
    assert not is_ki_tool(ki.root, ki.root / "tools/escape.py")
    assert not is_ki_tool(ki.root, ki.root / "SKILL.md")


def test_rejected_worktree_is_reused_then_validated_without_resetting_agent_work(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = flowrun.turn(project, [ki], _cfg(project), "cli", "kimi", None, "planning only")
    pj, inv = t.session.flow.plan.read_artifacts(t.planning_worktree)
    pj["goal"] = "Agent's carefully reviewed draft"
    pj["steps"][0]["inputs"] = ["missing-reference"]
    t.session.flow.plan.write_artifacts(t.planning_worktree, pj, inv)
    t.provider_succeeded = True
    rejected = flowrun.after(project, t, "saved")
    assert rejected.retry_planning and "missing-reference" in rejected.message
    t2 = flowrun.turn(project, [ki], _cfg(project), "cli", "kimi", None,
                      "planning only", replan_reason=rejected.message)
    recovered, recovered_inv = t2.session.flow.plan.read_artifacts(t2.planning_worktree)
    assert recovered == pj and recovered_inv == inv
    assert "missing-reference" in t2.extra_prompt
    recovered["steps"][0]["inputs"] = []
    t2.session.flow.plan.write_artifacts(t2.planning_worktree, recovered, recovered_inv)
    t2.provider_succeeded = True
    result = flowrun.after(project, t2, "repaired")
    assert result.request and not result.continue_now
    assert json.loads((project / "runs/plan.json").read_text())["goal"] == pj["goal"]
    assert not (project / ".geoforge/planning-last.json").exists()


def test_planning_only_never_auto_approves_even_a_fully_resolved_plan(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = _drive_planning(tmp_path, ki, project)
    t.confirmation_required = True
    result = flowrun.after(project, t, "saved")
    assert result.request and not result.continue_now
    assert not (project / "runs/approval.json").exists()


def test_partial_save_returns_to_agent_but_identical_failure_stops_repair(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    rejected_revisions = set()
    for attempt in range(2):
        t = flowrun.turn(project, [ki], _cfg(project), "cli", "kimi", None, "planning only")
        p = t.planning_worktree / "runs/plan.json"
        p.write_text(p.read_text())
        t.provider_succeeded = True
        result = flowrun.after(project, t, "I saved both (but actually only one)")
        assert result.retry_planning and "data-inventory.json" in result.message
        assert flowrun.claim_planning_repair(result, rejected_revisions) is (attempt == 0)
        assert not result.request and not (project / "runs/approval.json").exists()


def test_failed_provider_is_not_automatically_retried(tmp_path):
    project = _project(tmp_path); ki = _ki(tmp_path, "M")
    flowrun.pre(project, "run M for 2003", ["M"], [ki], None, None)
    t = flowrun.turn(project, [ki], _cfg(project), "cli", "codex", None, "planning only")
    t.provider_succeeded = False
    result = flowrun.after(project, t, "network failed")
    assert not flowrun.claim_planning_repair(result, set())
