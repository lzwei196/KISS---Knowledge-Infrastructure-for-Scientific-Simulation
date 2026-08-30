"""flowrun — one chat turn under the flow: resolve → plan → approve → execute → verify.

This is the desktop's driver for ``ki_tools_common.flow`` (plan v3 PART B, B1). gui.py
calls three functions and otherwise stays as it was:

  pre(...)    before the agent starts — handle the user's approval click, resolve which
              KIs the task involves (text + ticks), ask instead of guessing, move the
              state, and decide whether an agent turn is needed at all;
  turn(...)   inside _chat_with_models — open the FlowSession against the live KI roots,
              derive the draft plan (the app does this, not the agent), and return the
              prompt piece + tool policy + session rule for this state;
  after(...)  when the agent's turn ends — validate the plan files, show the approval
              card (auto-approve when nothing needs the user), or check receipts and
              move to COMPLETED / FAILED_VALIDATION.

The approval card reuses the desktop's existing "needs you" request (setup.request_user)
with two options: approve / modify. The user's click comes back as ``req["action"]`` on
the next turn, exactly like every other request.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import flowgate, projectrun, setup as setup_flow

APPROVAL_REQUEST_ID_PREFIX = "flow-approve-"
REPLAN_MARKER = "REPLAN_REQUIRED"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def catalogue_entries(catalog) -> list[dict]:
    return [{"id": ki.name, "name": ki.name, "ki_path": str(ki.root)} for ki in catalog]


def _flow():
    return flowgate.load()


def _data_roots(flow, repo_root: Path | None):
    """Bundled planner data (flow/data) if present, else the server's ata-kdt tree."""
    import ki_tools_common.flow as _pkg
    bundled = Path(_pkg.__file__).resolve().parent / "data"
    if (bundled / "cards").is_dir():
        return flow.plan.DataRoots.bundled(bundled)
    return flow.plan.DataRoots.server()


def display_stage(flow, state) -> str:
    return flow.states.DISPLAY_STAGE.get(state, "preparing")


# ---------------------------------------------------------------------------
# pre: resolution + approval handling
# ---------------------------------------------------------------------------

@dataclass
class Pre:
    names: list[str]                       # KI names for this turn (may include added partners)
    message: str | None = None             # reply INSTEAD of an agent turn (question / refusal)
    gated: bool = True                     # False = ordinary chat, no flow
    replan_reason: str = ""


def pre(project: Path, text: str, names: list[str], catalog, action: dict | None,
        pending: dict | None, note: str = "", couplings_dir: Path | None = None,
        setup_ok: bool = True) -> Pre:
    flow = _flow()
    ctx = flow.states.FlowContext.load(project)
    S = flow.states.State

    # 1. the user's answer to the approval card
    if pending and str(pending.get("id", "")).startswith(APPROVAL_REQUEST_ID_PREFIX) and action \
            and str(action.get("request_id")) == str(pending.get("id")):
        choice = str(action.get("option_id") or "")
        setup_flow.clear_request(project)
        if choice == "approve":
            verdict = flow.approval.check(project)
            if verdict != "OK":
                # (re)approve the CURRENT plan files by the user's click
                flow.approval.approve(project, {"note": note} if note else {}, by="user")
            ctx.move("approved", {"approval": flow.approval.check(project)})
            _start_execution(flow, ctx, project, setup_ok)
            return Pre(names=list(ctx.selected_kis or names), message=None)
        # modify → back to planning with the note as the reason
        ctx.move("modify")
        projectrun.set_stage(project, display_stage(flow, ctx.state), "Revising the plan")
        return Pre(names=list(ctx.selected_kis or names), replan_reason=note or "user asked for changes")

    # 2. ordinary chat stays ungated until a scientific task starts a flow
    if ctx.state is S.NEW and not flow.resolve.is_scientific_task(text) and not names:
        return Pre(names=list(names), gated=False)

    # 3. resolve which KIs the task involves — never guess
    cat = catalogue_entries(catalog)
    pairs = flow.resolve.coupling_pairs(couplings_dir) if couplings_dir else None
    res = flow.resolve.resolve_kis(text, list(ctx.selected_kis or names), cat, couplings=pairs)
    if ctx.state in (S.NEW,):
        ctx.move("task_received")
    if ctx.state is S.RESOLVING_KIS:
        if res.ambiguous or res.unknown:
            ctx.move("ambiguous")
            ctx.save()
            q = []
            for tok, cands in res.ambiguous.items():
                q.append(f"“{tok}” could be {', '.join(cands)} — which one?")
            for tok in res.unknown:
                q.append(f"“{tok}” is not a model I have a Knowledge Infrastructure for. Do you "
                         f"mean one of the installed models, or should we leave it out?")
            projectrun.set_stage(project, display_stage(flow, ctx.state), "Which model?")
            return Pre(names=res.resolved, message="Before planning I need one thing:\n- " + "\n- ".join(q))
        if not res.resolved:
            ctx.save()
            return Pre(names=[], message=None)      # auto-mode catalogue turn picks the model
        ctx.selected_kis = list(res.resolved)
        ctx.move("kis_resolved", {"selected_kis": ctx.selected_kis})
        projectrun.select_kis(project, ctx.selected_kis)
        projectrun.set_stage(project, display_stage(flow, ctx.state), "Planning the run")
        return Pre(names=list(ctx.selected_kis))
    if ctx.state is S.WAITING_FOR_USER and (res.resolved and not res.ambiguous and not res.unknown):
        # the user answered the "which model?" question
        ctx.selected_kis = list(res.resolved)
        ctx.move("kis_resolved", {"selected_kis": ctx.selected_kis})
        projectrun.select_kis(project, ctx.selected_kis)
        return Pre(names=list(ctx.selected_kis))
    ctx.save()
    return Pre(names=list(ctx.selected_kis or res.resolved or names))


def _start_execution(flow, ctx, project: Path, setup_ok: bool) -> None:
    """APPROVED → EXECUTING when every selected KI's software is verified, else the SETUP
    sub-flow (plan v2 §5 item 2). The execution turn starts a fresh agent session."""
    if setup_ok:
        ctx.move("execution_started", {"setup_verified": True})
        projectrun.set_stage(project, display_stage(flow, ctx.state), "Approved — running the plan")
    else:
        ctx.move("setup_needed")
        projectrun.set_stage(project, display_stage(flow, ctx.state),
                             "Approved — the scientific software must be set up first")


# ---------------------------------------------------------------------------
# turn: what this state's agent turn gets
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    session: object                        # flowgate.FlowSession
    execute: bool                          # compose(..., execute=)
    extra_prompt: str                      # appended to the [TASK]
    drop_scope_rules: bool                 # SCOPE_FIRST_RULES are the flow's job now
    policy: object                         # flow.policy.ProviderPolicy
    fingerprint_extra: str                 # forces a fresh CLI session when the state changes
    planning_worktree: Path | None = None  # codex/kimi PLANNING: run here, harvest plan files
    wrappers: dict = field(default_factory=dict)


def turn(project: Path, resolved, cfg, provider_kind: str, provider_name: str,
         repo_root: Path | None, goal: str, replan_reason: str = "",
         base_allowed_tools: list[str] | None = None) -> Turn | None:
    """resolved = the live KI objects (name, root) the agent will see."""
    flow = _flow()
    S = flow.states.State
    ki_roots = {k.name: Path(k.root) for k in resolved}
    fs = flowgate.FlowSession.open(project, ki_roots, python=str(getattr(cfg, "python", "") or "python3"))
    state = fs.state
    provider = "api" if provider_kind == "api" else provider_name
    wrappers = {"run_tool": "kiss run-tool", "fetch": "kiss fetch"} if provider != "api" else None

    if state in (S.PLANNING, S.REPLAN_REQUIRED):
        # the app derives the draft plan; the agent corrects it
        if fs.plan is None or fs.inventory is None or state is S.REPLAN_REQUIRED and replan_reason:
            roots = _data_roots(flow, repo_root)
            intent = _intent_from_goal(goal)
            try:
                _full, pj, inv = flow.plan.derive(list(ki_roots), intent, goal, roots, ki_roots)
            except Exception as e:  # noqa: BLE001 — a missing card is a planning fact, not a crash
                pj, inv = {"schema_version": "1.0", "goal": goal, "selected_kis": list(ki_roots),
                           "coupling": [], "intent": intent, "steps": [], "scientific_choices": [],
                           "unresolved_questions": [f"draft plan could not be derived: {e}"],
                           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, \
                          {"schema_version": "1.0", "items": []}
            if fs.plan is None or fs.inventory is None:
                flow.plan.write_artifacts(project, pj, inv)
                fs.reload_artifacts()
        edges = flow.resolve.couplings_for(list(ki_roots), _data_roots(flow, repo_root).couplings, one_end=True)
        partners = [e["partner_missing"] for e in edges if e.get("partner_missing")]
        extra = flow.contracts.planning_block(ki_roots, fs.plan or {}, fs.inventory or {}, project,
                                              partners_to_ask=sorted(set(partners)) or None,
                                              replan_reason=replan_reason)
        pp = flow.policy.for_state(state, provider, project, ki_roots,
                                   python=str(getattr(cfg, "python", "") or "python3"))
        wt = _planning_worktree(project) if pp.planning_worktree else None
        return Turn(fs, False, extra, True, pp, f"flow:{state.value}:{fs.approval_id}", wt, wrappers or {})

    if state is S.EXECUTING:
        if fs.approval_status() != "OK":
            fs.move("drift")
            projectrun.set_stage(project, display_stage(flow, fs.state), "Plan changed — needs re-approval")
            return turn(project, resolved, cfg, provider_kind, provider_name, repo_root, goal,
                        replan_reason="the plan files changed after approval")
        extra = flow.contracts.execution_block(ki_roots, fs.plan or {}, fs.approval_doc or {}, project,
                                               provider=provider, wrappers=wrappers)
        pp = flow.policy.for_state(state, provider, project, ki_roots,
                                   python=str(getattr(cfg, "python", "") or "python3"),
                                   base_allowed_tools=base_allowed_tools, wrappers=wrappers)
        fs.ctx.enforcement = flow.states.Enforcement(pp.enforcement.value); fs.ctx.save()
        return Turn(fs, True, extra, True, pp, f"flow:{state.value}:{fs.approval_id}", None, wrappers or {})

    if state in (S.SETUP_REQUIRED, S.SETUP_RUNNING):
        pp = flow.policy.for_state(state, provider, project, ki_roots)
        return Turn(fs, False, "[SETUP] The KI software is not verified yet. Finish setup; the "
                    "approved plan runs afterwards in a new session.", False, pp,
                    f"flow:{state.value}", None, {})

    # PLAN_REVIEW / WAITING_FOR_USER / APPROVED / VERIFYING / COMPLETED / FAILED*: read-only turn
    pp = flow.policy.for_state(state, provider, project, ki_roots)
    extra = (f"[FLOW STATE: {state.value}] Answer the user's question from the project files. Do not "
             f"run, download, or write inputs; " + flowgate._hint(state))
    return Turn(fs, False, extra, True, pp, f"flow:{state.value}:{fs.approval_id}", None, {})


def _intent_from_goal(goal: str) -> dict:
    """Cheap intent: years and a lat/lon pair when the user typed them. Everything else is a
    planning question (the agent and the user fill it in)."""
    import re
    intent: dict = {"user_message": goal[:2000]}
    years = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", goal)]
    if years:
        intent["start_year"], intent["end_year"] = min(years), max(years)
    m = re.search(r"(-?\d{1,2}\.\d+)\s*[,;]\s*(-?\d{1,3}\.\d+)", goal)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if abs(a) <= 90 and abs(b) <= 180:
            intent["lat"], intent["lon"] = a, b
    return intent


def _planning_worktree(project: Path) -> Path:
    """codex/kimi have no read-only mode: plan in a throwaway copy of the project (no outputs,
    no receipts); only the two plan files are harvested back by after()."""
    wt = Path(project) / ".geoforge" / "planning_worktree"
    if wt.exists():
        shutil.rmtree(wt, ignore_errors=True)
    shutil.copytree(project, wt, ignore=shutil.ignore_patterns(".geoforge", "outputs", "artifacts",
                                                               "models", "*.tmp"))
    return wt


# ---------------------------------------------------------------------------
# after: validate / approve / verify
# ---------------------------------------------------------------------------

def _harvest_worktree(project: Path, wt: Path) -> None:
    for rel in ("runs/plan.json", "runs/data-inventory.json"):
        src = wt / rel
        if src.is_file():
            (project / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, project / rel)
    shutil.rmtree(wt, ignore_errors=True)


def _card(flow, fs, plan: dict, inv: dict, provider_note: str) -> dict:
    """The PLAN_REVIEW card, in the shape setup.request_user renders (issue §UI)."""
    can = [f"prepare inputs for {k}" for k in plan.get("selected_kis") or []]
    edges = [c.get("edge_id") for c in plan.get("coupling") or [] if c.get("edge_id")]
    if edges:
        can.append("couple: " + ", ".join(edges))
    missing = [f"{it.get('id')} (for {', '.join(it.get('required_by') or [])})"
               for it in inv.get("items") or [] if it.get("status") == "missing"]
    decide = [f"{c.get('kind')}: {', '.join(map(str, c.get('options') or []))} (suggested {c.get('picked')})"
              for c in plan.get("scientific_choices") or [] if c.get("high_impact") and not c.get("decision")]
    resolved = sum(1 for it in inv.get("items") or [] if it.get("status") in ("resolved", "ready"))
    msg = (f"What I understood\n  {plan.get('goal')}\n\n"
           f"GeoForge can do itself\n  " + ("\n  ".join("✓ " + c for c in can) or "—") + "\n\n"
           f"Data: {resolved} inputs resolved, {len(missing)} missing"
           + ("\n  " + "\n  ".join("! " + m for m in missing[:8]) if missing else "") + "\n\n"
           + ("You decide\n  " + "\n  ".join(decide) + "\n\n" if decide else "")
           + f"Steps: {len(plan.get('steps') or [])}   Tool policy: {provider_note}\n"
           f"Details: runs/plan.json, runs/data-inventory.json")
    return {
        "id": APPROVAL_REQUEST_ID_PREFIX + fs.flow.plan.sha256(plan)[:10],
        "kind": "choice", "title": "Approve the plan?", "message": msg, "allow_note": True,
        "options": [
            {"id": "approve", "label": "Approve and start",
             "description": "Execution starts in a fresh session with the approved plan; every run and download gets a receipt.",
             "response": "Approved. Start the execution."},
            {"id": "modify", "label": "Modify the plan",
             "description": "Tell me what to change in the note; I will revise the plan and ask again.",
             "response": "Please revise the plan."},
        ],
    }


@dataclass
class Result:
    request: dict | None = None     # the approval card (setup.request_user doc) to show
    continue_now: bool = False      # auto-approved: start the execution turn right away


def after(project: Path, t: Turn | None, reply: str, provider_note: str = "",
          setup_ok: bool = True) -> Result:
    """Close the turn: validate the plan / show the approval card / check receipts."""
    if t is None:
        return Result()
    flow = t.session.flow
    S = flow.states.State
    fs = t.session
    fs.ctx = flow.states.FlowContext.load(project)     # tools may have moved nothing, but reload
    state = fs.ctx.state
    if t.planning_worktree:
        _harvest_worktree(project, t.planning_worktree)
    fs.reload_artifacts()

    if state in (S.PLANNING, S.REPLAN_REQUIRED):
        pj, inv = fs.plan, fs.inventory
        if pj is None or inv is None:
            projectrun.set_stage(project, display_stage(flow, state), "Plan files missing — ask the agent again")
            return Result()
        errs = flow.plan.validate(pj, inv, list(fs.ki_roots), fs.ki_roots)
        if errs:
            (project / "runs" / "plan-validation.txt").write_text("\n".join(errs), encoding="utf-8")
            projectrun.set_stage(project, display_stage(flow, state),
                                 f"Plan needs fixes ({len(errs)}) — see runs/plan-validation.txt")
            return Result()
        fs.move("plan_written", {"plan_valid": True})
        ok, why = flow.approval.may_auto_approve(pj, inv)
        ready = flow.plan.validate(pj, inv, list(fs.ki_roots), fs.ki_roots, for_execution=True)
        if ok and not ready:
            flow.approval.approve(project, {}, by="auto")
            fs.move("approved", {"approval": flow.approval.check(project)})
            _start_execution(flow, fs.ctx, project, setup_ok)
            return Result(continue_now=fs.ctx.state is S.EXECUTING)
        card = _card(flow, fs, pj, inv, provider_note)
        if not ok:
            card["message"] += "\n\nWaiting on you\n  " + "\n  ".join(why[:8])
        if ready:
            card["message"] += "\n\nNot ready to execute yet\n  " + "\n  ".join(ready[:6])
        doc = setup_flow.request_user(project, card)
        doc["id"] = card["id"]
        (Path(project) / setup_flow.REQUEST_FILE).write_text(json.dumps(doc, indent=2), encoding="utf-8")
        fs.move("needs_user")
        projectrun.report(project, {"status": "waiting_for_user", "summary": card["title"], "blocker": doc},
                          source="flow")
        return Result(request=doc)

    if state is S.EXECUTING:
        if REPLAN_MARKER in (reply or ""):
            fs.move("replan")
            flow.approval.revoke(project, "agent reported REPLAN_REQUIRED")
            projectrun.set_stage(project, display_stage(flow, fs.state), "The agent needs a plan change")
            return Result()
        ev = fs.evidence(enforcement=fs.ctx.enforcement.value)
        (project / "runs" / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
        if ev["validation"] == "failed":
            fs.move("run_finished"); fs.move("validation_failed")
            projectrun.set_stage(project, display_stage(flow, fs.state),
                                 "A run failed validation — see runs/evidence.json")
        elif ev["receipts_verified"] and ev["validation"] == "passed":
            fs.move("run_finished")
            fs.move("validated", {"receipts_verified": True, "validation": "passed"})
            projectrun.set_stage(project, display_stage(flow, fs.state), "Completed — every step has a verified receipt")
        else:
            missing = ev.get("steps_missing") or []
            projectrun.set_stage(project, display_stage(flow, state),
                                 f"Running — {len(ev.get('steps_passed') or [])} steps done, "
                                 f"{len(missing)} to go" + (f", {len(ev['unreceipted_artifacts'])} unreceipted files"
                                                             if ev.get("unreceipted_artifacts") else ""))
        return Result()
    return Result()


# ---------------------------------------------------------------------------
# small helpers gui.py calls
# ---------------------------------------------------------------------------

def couplings_dir() -> Path | None:
    """Where the coupling configs live: the bundled flow/data copy, else the server tree."""
    try:
        flow = _flow()
        roots = _data_roots(flow, None)
        return roots.couplings if Path(roots.couplings).is_dir() else None
    except Exception:  # noqa: BLE001
        return None


def setup_turn(project: Path, resolved, cfg, provider_kind: str, provider_name: str) -> Turn | None:
    """A software-setup turn under the flow: the SETUP sub-flow, never a scientific run."""
    flow = _flow()
    S = flow.states.State
    ki_roots = {k.name: Path(k.root) for k in resolved}
    fs = flowgate.FlowSession.open(project, ki_roots, python=str(getattr(cfg, "python", "") or "python3"))
    if fs.state is S.APPROVED:
        fs.move("setup_needed")
    if fs.state is S.SETUP_REQUIRED:
        fs.move("setup_started")
    provider = "api" if provider_kind == "api" else provider_name
    pp = flow.policy.for_state(fs.state, provider, project, ki_roots)
    projectrun.set_stage(project, display_stage(flow, fs.state), "Setting up the scientific software")
    return Turn(fs, False, "", False, pp, f"flow:{fs.state.value}", None, {})


def setup_verified(project: Path, resolved, cfg) -> None:
    """Called when the KI's preflight passed after a setup turn: SETUP_RUNNING → VERIFIED → APPROVED."""
    flow = _flow()
    S = flow.states.State
    ki_roots = {k.name: Path(k.root) for k in resolved}
    fs = flowgate.FlowSession.open(project, ki_roots)
    if fs.state is S.SETUP_RUNNING:
        fs.move("setup_verified", {"preflight_ok": True})
        fs.move("resume")
        projectrun.set_stage(project, display_stage(flow, fs.state), "Software verified — the approved plan can run")


def policy_for_cli(t: Turn, provider_name: str, pol) -> object:
    """Recompute the flow policy for a CLI provider with the desktop's base grants (only
    their path-scoped READ grants are reused; see flow.policy._claude_executing_tools)."""
    flow = t.session.flow
    S = flow.states.State
    base: list[str] | None = None
    if provider_name == "claude" and pol is not None:
        from . import policy as _pol
        args, _enf = _pol.claude_args(pol)
        if len(args) >= 2 and args[0] == "--allowedTools":
            base = args[1:]
    if t.session.state is S.EXECUTING:
        return flow.policy.for_state(S.EXECUTING, provider_name, t.session.project, t.session.ki_roots,
                                     python=t.session.python, base_allowed_tools=base, wrappers=t.wrappers)
    return t.policy


def describe_policy(t: Turn) -> str:
    try:
        return t.session.flow.policy.describe(t.policy)
    except Exception:  # noqa: BLE001
        return ""
