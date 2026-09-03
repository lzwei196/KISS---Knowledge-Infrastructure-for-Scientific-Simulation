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
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import flowgate, projectrun, setup as setup_flow

APPROVAL_REQUEST_ID_PREFIX = "flow-approve-"
REPLAN_MARKER = "REPLAN_REQUIRED"
INTAKE_MARKER = "GEOFORGE_INTAKE"
_INTAKE_PATTERN = re.compile(
    r"<!--\s*" + INTAKE_MARKER + r"\s*(\{.*?\})\s*-->", re.S)


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


def _explicit_positive_model_mention(text: str, model: str) -> bool:
    """True when *model* is actually named in prose and is not locally negated.

    Catalogue resolution deliberately has fuzzy aliases, which is useful in Auto-KI
    mode but unsafe for expanding a pinned selection: ``grid cell`` has matched
    Cell2Fire, and ``do not invoke CaMa-Flood`` still contains a literal model name.
    """
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", model) if p]
    if not parts:
        return False
    aliases = [r"[\s_-]*".join(map(re.escape, parts))]
    # Coupling shorthand commonly uses the distinctive first component (VIC-CaMa).
    if len(parts) > 1 and len(parts[0]) >= 4:
        aliases.append(re.escape(parts[0]))
    negation = re.compile(
        r"(?:do\s+not|don't|without|exclude|excluding|not\s+using|no|"
        r"不要|不使用|不用|不调用|禁止|排除)[^.;,，。]{0,32}$", re.I)
    for alias in aliases:
        for match in re.finditer(r"(?<![A-Za-z0-9])" + alias + r"(?![A-Za-z0-9])",
                                 text, re.I):
            if not negation.search(text[max(0, match.start() - 48):match.start()]):
                return True
    return False


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
        if choice == "approve":
            pj, inv = flow.plan.read_artifacts(project)
            review = pending.get("review") or {}
            if (pj is None or inv is None or review.get("plan_sha256") != flow.plan.sha256(pj)
                    or review.get("inventory_sha256") != flow.plan.sha256(inv)):
                setup_flow.clear_request(project)
                ctx.move("modify")
                return Pre(names=list(ctx.selected_kis or names),
                           replan_reason="The plan or inventory changed after review. Review this revision before approval.")
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

    # 2. ordinary chat stays ungated until a scientific task starts a flow — with or
    #    without a pinned KI ("thanks" in a VIC chat is not a run request)
    if ctx.state is S.NEW and not flow.resolve.is_scientific_task(text):
        return Pre(names=list(names), gated=False)

    # 3. resolve which KIs the task involves — never guess
    cat = catalogue_entries(catalog)
    pairs = flow.resolve.coupling_pairs(couplings_dir) if couplings_dir else None
    res = flow.resolve.resolve_kis(text, list(ctx.selected_kis or names), cat, couplings=pairs)
    if ctx.state in (S.NEW,):
        ctx.move("task_received")
    if ctx.state is S.RESOLVING_KIS:
        # A free-language first message belongs to the task-understanding Agent, not to a
        # collection of host regexes.  Known-name matches are useful hints, but are not a
        # semantic decision and must not produce host-authored clarification questions.
        # A non-empty ``names`` list is different: the user explicitly pinned a KI in the UI.
        # Once the user explicitly pins a KI, unrelated uppercase terms in the
        # scientific request (NASA POWER, API, DEM, CMFD, etc.) are data/tool
        # vocabulary, not evidence that a second unknown model was requested.
        # A pinned selection is authoritative by default.  Do not fuzzily expand it
        # from prose: a
        # task may mention another model in a comparison or a negation ("do not
        # invoke CaMa-Flood"), and ordinary terms such as "grid cell" can also
        # collide with catalogue aliases (for example Cell2Fire).  Coupled runs
        # must therefore be pinned as a multi-KI selection by the UI/intake.
        if not names:
            ctx.save()
            projectrun.set_stage(project, display_stage(flow, ctx.state),
                                 "Understanding the task and choosing the KI")
            return Pre(names=[], message=None)
        selected = list(dict.fromkeys(names))
        selected.extend(k for k in res.resolved if k not in selected
                        and _explicit_positive_model_mention(text, k))
        ctx.selected_kis = selected
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
    kind: str = "planning"                 # planning | execution | setup | readonly | auto
    draft_before: dict = field(default_factory=dict)
    project_before: dict = field(default_factory=dict)
    provider_succeeded: bool | None = None
    confirmation_required: bool = False


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
    wrappers = wrapper_commands() if provider != "api" else None

    if state in (S.PLANNING, S.REPLAN_REQUIRED):
        # the app derives the draft plan; the agent corrects it
        if fs.plan is None or fs.inventory is None or state is S.REPLAN_REQUIRED and replan_reason:
            roots = _data_roots(flow, repo_root)
            intake = projectrun.load(project).get("intake") or {}
            intent = _intent_from_goal(goal + " " + str(intake.get("period") or ""))
            for key in ("understanding", "study_area", "period", "process", "scenario",
                        "requested_outputs"):
                if intake.get(key):
                    intent[key] = intake[key]
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
        pp = flow.policy.for_state(state, provider, project, ki_roots,
                                   python=str(getattr(cfg, "python", "") or "python3"))
        wt = _planning_worktree(project) if pp.planning_worktree else None
        draft_root = wt or project
        draft_plan, draft_inv = flow.plan.read_artifacts(draft_root)
        extra = flow.contracts.planning_block(ki_roots,
                                              draft_plan if isinstance(draft_plan, dict) else {},
                                              draft_inv if isinstance(draft_inv, dict) else {}, draft_root,
                                              partners_to_ask=sorted(set(partners)) or None,
                                              replan_reason=replan_reason)
        extra += (f"\n[PLAN HANDOFF] Save BOTH JSON files under {draft_root / 'runs'}, even if "
                  "your review leaves their content unchanged. The app must observe a submission "
                  "from this turn; an untouched auto-draft is never a completed plan. "
                  "For API providers call write_plan. Stop after saving.\n")
        if wt:
            extra += (f"Original project {project} is READ ONLY. It is for inventory inspection, "
                      f"not plan writes. The only draft submission location is {draft_root}.\n")
        errors = project / "runs" / "plan-validation.txt"
        if errors.is_file():
            extra += "\n[PREVIOUS SUBMISSION NEEDS REPAIR]\n" + errors.read_text(encoding="utf-8")[:16000]
        import uuid
        import re
        confirm = bool(re.search(r"未确认|先只|只做|先.*规划|plan(?:ning)?[- ]only|do not|don't|before.*approv", goal, re.I))
        return Turn(fs, False, extra, True, pp, f"flow:{state.value}:{uuid.uuid4().hex}", wt, wrappers or {},
                    draft_before=_plan_versions(draft_root), project_before=_plan_versions(project),
                    confirmation_required=confirm)

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
        return Turn(fs, True, extra, True, pp, f"flow:{state.value}:{fs.approval_id}", None, wrappers or {},
                    kind="execution")

    if state in (S.SETUP_REQUIRED, S.SETUP_RUNNING):
        pp = flow.policy.for_state(state, provider, project, ki_roots)
        return Turn(fs, False, "[SETUP] The KI software is not verified yet. Finish setup; the "
                    "approved plan runs afterwards in a new session.", False, pp,
                    f"flow:{state.value}", None, {}, kind="setup")

    # PLAN_REVIEW / WAITING_FOR_USER / APPROVED / VERIFYING / COMPLETED / FAILED*: read-only turn
    pp = flow.policy.for_state(state, provider, project, ki_roots)
    extra = (f"[FLOW STATE: {state.value}] Answer the user's question from the project files. Do not "
             f"run, download, or write inputs; " + flowgate._hint(state))
    return Turn(fs, False, extra, True, pp, f"flow:{state.value}:{fs.approval_id}", None, {}, kind="readonly")


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
    import uuid
    wt = Path(project) / ".geoforge" / "planning" / uuid.uuid4().hex
    (wt / "runs").mkdir(parents=True)
    source = project
    previous = project / ".geoforge" / "planning-last.json"
    try:
        candidate = Path(json.loads(previous.read_text(encoding="utf-8"))["draft_root"]).resolve()
        if (project / ".geoforge" / "planning").resolve() in candidate.parents:
            if len(_plan_versions(candidate)) == 2:
                source = candidate
    except (OSError, ValueError, KeyError, TypeError):
        pass
    # Only the drafts are copied, never inputs, binaries, approval keys or outputs.
    for rel in ("runs/plan.json", "runs/data-inventory.json"):
        shutil.copy2(source / rel, wt / rel)
    return wt


# ---------------------------------------------------------------------------
# after: validate / approve / verify
# ---------------------------------------------------------------------------

def _plan_versions(root: Path) -> dict:
    """Detect saves, including a deliberate rewrite of an unchanged reviewed draft."""
    import hashlib
    versions = {}
    for rel in ("runs/plan.json", "runs/data-inventory.json"):
        p = root / rel
        try:
            if p.is_symlink():
                continue
            st = p.stat()
            versions[rel] = (st.st_mtime_ns, st.st_ctime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
        except OSError:
            pass
    return versions


def _planning_failure(project: Path, t: Turn, errors: list[str], *, repair: bool = False) -> "Result":
    message = "Plan was not submitted for approval:\n- " + "\n- ".join(errors[:30])
    (project / "runs" / "plan-validation.txt").write_text(message, encoding="utf-8")
    projectrun.report(project, {"status": "needs_attention", "summary": message}, source="flow")
    if t.planning_worktree:
        meta = project / ".geoforge" / "planning-last.json"
        meta.write_text(json.dumps({"draft_root": str(t.planning_worktree)}), encoding="utf-8")
    # Identical rejected revisions must not trigger an infinite retry loop.
    versions = _plan_versions(t.planning_worktree or project)
    fingerprint = t.session.flow.plan.sha256({"errors": errors, "files": {k: v[-1] for k, v in versions.items()}})
    return Result(message=message, retry_planning=repair, revision=fingerprint)


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
    message: str = ""
    retry_planning: bool = False
    revision: str = ""


def claim_planning_repair(result: Result, rejected: set[str]) -> bool:
    """Retry changed rejected drafts, but never spin on the same failure/content."""
    if not result.retry_planning or not result.revision or result.revision in rejected:
        return False
    rejected.add(result.revision)
    return True


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
    fs.reload_artifacts()
    if t.kind in ("setup", "auto") and state is S.EXECUTING:
        return Result(continue_now=True)          # setup verified → run the approved plan now

    if state in (S.PLANNING, S.REPLAN_REQUIRED):
        if t.provider_succeeded is False or getattr(fs, "provider_succeeded", None) is False:
            return _planning_failure(project, t, ["The provider failed or was interrupted. Your draft is preserved; retry planning."])
        draft_root = t.planning_worktree or project
        current = _plan_versions(draft_root)
        saved_both = len(current) == 2 and all(current.get(k) != v for k, v in t.draft_before.items())
        api_submission = getattr(fs, "plan_submission", None)
        pj, inv = flow.plan.read_artifacts(draft_root)
        if not saved_both and not api_submission:
            unsaved = [k for k in ("runs/plan.json", "runs/data-inventory.json")
                       if k not in current or current[k] == t.draft_before.get(k)]
            return _planning_failure(project, t, [
                "No current-turn submission of both plan files. The generated draft is not an agent-reviewed plan.",
                "Save these files again even if unchanged: " + ", ".join(unsaved),
            ], repair=t.provider_succeeded is True)
        if pj is None or inv is None:
            return _planning_failure(project, t, ["Both plan files must contain valid JSON objects."], repair=True)
        if api_submission and api_submission != (flow.plan.sha256(pj), flow.plan.sha256(inv)):
            return _planning_failure(project, t, ["The files changed after write_plan submitted them. Submit the current revision again."])
        errs = flow.plan.validate(pj, inv, list(fs.ki_roots), fs.ki_roots)
        if errs:
            return _planning_failure(project, t, errs, repair=True)
        if t.planning_worktree:
            if _plan_versions(project) != t.project_before:
                return _planning_failure(project, t, ["The original plan changed while planning. Both revisions are preserved; review and resubmit instead of overwriting."])
            flow.plan.write_artifacts(project, pj, inv)
            fs.reload_artifacts()
        # The approval UI is bound to exactly the reviewed pair, not just a plan filename.
        receipt = {"plan_sha256": flow.plan.sha256(pj), "inventory_sha256": flow.plan.sha256(inv),
                   "turn": t.fingerprint_extra, "submitted_at": time.time()}
        (project / "runs" / "plan-review.json").write_text(json.dumps(receipt), encoding="utf-8")
        (project / "runs" / "plan-validation.txt").unlink(missing_ok=True)
        (project / ".geoforge" / "planning-last.json").unlink(missing_ok=True)
        fs.move("plan_written", {"plan_valid": True})
        ok, why = flow.approval.may_auto_approve(pj, inv)
        if t.confirmation_required:
            ok = False
            why.append("You requested plan review before any execution.")
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
        doc["review"] = receipt
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

def wrapper_commands() -> dict:
    """The receipt wrappers a CLI agent must use (plan v3 B7 / 06 §3.6). They are the app
    itself — the frozen binary accepts CLI sub-commands; from source `python -m kiss_cli`.
    The exact string is also what the Claude Bash allow-list grants — nothing else runs.

    codex desktop review #4: the frozen binary is "GeoForge Desktop" (a space), which is
    neither shell-safe nor a stable allow-list prefix. So the wrapper is a tiny launcher
    script at a space-free path (``~/.kiss/bin/geoforge-flow``) that execs the real binary."""
    import os as _os
    import shlex
    import sys as _sys
    if not getattr(_sys, "frozen", False):
        base = f"{_sys.executable} -m kiss_cli"
        if " " in _sys.executable:
            base = f"{shlex.quote(_sys.executable)} -m kiss_cli"
        return {"run_tool": f"{base} run-tool", "fetch": f"{base} fetch"}
    launcher = _launcher_path()
    if launcher is None:
        base = shlex.quote(_sys.executable)
    else:
        base = str(launcher)
    return {"run_tool": f"{base} run-tool", "fetch": f"{base} fetch"}


def _launcher_path() -> Path | None:
    """Create (once) a launcher for the frozen binary at a path without spaces."""
    import os as _os
    import stat
    import sys as _sys
    exe = Path(_sys.executable)
    home = Path.home()
    # user-owned locations only (kimi desktop R2 #3: never a world-writable temp dir). When
    # every candidate has a space in it the caller quotes the binary path instead.
    candidates = [home / ".kiss" / "bin", home / ".config" / "geoforge" / "bin"]
    for d in candidates:
        if " " in str(d):
            continue
        try:
            d.mkdir(parents=True, exist_ok=True)
            try:
                _os.chmod(d, 0o755)
            except OSError:
                pass
            if _os.name == "nt":
                p = d / "geoforge-flow.cmd"
                body = f'@echo off\r\n"{exe}" %*\r\n'
            else:
                p = d / "geoforge-flow"
                body = f'#!/bin/sh\nexec "{exe}" "$@"\n'
            # always point at the CURRENT executable (an old launcher must not exec a stale app)
            if not p.is_file() or p.read_text(encoding="utf-8", errors="replace") != body:
                p.write_text(body, encoding="utf-8")
            if _os.name != "nt":
                p.chmod(0o755)
            return p
        except OSError:
            continue
    return None


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
    return Turn(fs, False, "", False, pp, f"flow:{fs.state.value}", None, {}, kind="setup")


def setup_verified(project: Path, resolved, cfg) -> None:
    """Called when the KI's preflight passed after a setup turn: SETUP_RUNNING → VERIFIED → APPROVED."""
    flow = _flow()
    S = flow.states.State
    ki_roots = {k.name: Path(k.root) for k in resolved}
    fs = flowgate.FlowSession.open(project, ki_roots)
    if fs.state is S.SETUP_RUNNING:
        fs.move("setup_verified", {"preflight_ok": True})
        fs.move("resume")                                   # → APPROVED
        _start_execution(flow, fs.ctx, project, True)      # → EXECUTING (codex R2 #2)
        projectrun.set_stage(project, display_stage(flow, fs.state), "Software verified — running the approved plan")


def policy_for_cli(t: Turn, provider_name: str, pol) -> object:
    """Recompute the flow policy for a CLI provider with the desktop's base grants (only
    their path-scoped READ grants are reused; see flow.policy._claude_executing_tools)."""
    flow = t.session.flow
    S = flow.states.State
    if t.kind == "setup" or t.session.state in (S.SETUP_REQUIRED, S.SETUP_RUNNING, S.SETUP_VERIFIED):
        # kimi desktop R2 #1: the setup sub-flow is driven by the desktop's own setup grants
        # (_grant_setup_execution); a flow policy here would replace them with read-only argv
        return None
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


def auto_turn(project: Path, provider_kind: str, provider_name: str) -> Turn | None:
    """The 'choose a model' turn when nothing resolved (codex desktop review #1/#2): a real
    FlowSession in RESOLVING_KIS (API tools filtered to read-only + report/request; CLI argv
    read-only), never project writes, never a worktree. Providers that cannot be gated are
    refused for scientific projects."""
    flow = _flow()
    fs = flowgate.FlowSession.open(project, {})
    provider = "api" if provider_kind == "api" else provider_name
    if provider in flow.policy.NOT_OFFERED:
        raise flowgate.FlowDenied(
            f"{provider} cannot be held to the planning gate; choose Claude Code, Codex, Kimi or "
            f"an API provider for scientific projects")
    pp = flow.policy.for_state(fs.state, provider, project, {})
    return Turn(fs, False, "", False, pp, f"flow:{fs.state.value}", None, {}, kind="auto")


def setup_allowed(project: Path) -> bool:
    """Scientific-software setup may run only after the plan is approved (APPROVED →
    SETUP_REQUIRED → SETUP_RUNNING), or in a project with no flow at all."""
    if not (Path(project) / "runs" / "flow-state.json").is_file():
        return True
    flow = _flow()
    S = flow.states.State
    st = flow.states.FlowContext.load(project).state
    return st in (S.APPROVED, S.SETUP_REQUIRED, S.SETUP_RUNNING, S.SETUP_VERIFIED)


def provider_refusal(provider_kind: str, provider_name: str) -> str | None:
    """Why a provider may not drive a flow-managed (scientific) chat, or None (kimi desktop
    review #2: NOT_OFFERED providers must be refused, not merely labelled)."""
    provider = "api" if provider_kind == "api" else (provider_name or "")
    try:
        flow = _flow()
    except Exception:  # noqa: BLE001
        return None
    if provider in flow.policy.NOT_OFFERED:
        return (f"{provider} cannot be held to the planning gate (no per-tool policy); for scientific "
                f"projects use Claude Code, Codex, Kimi or an API provider.")
    return None


def _intake_from_reply(reply: str) -> dict | None:
    """Read the invisible CLI handoff marker from an Agent response.

    Direct APIs use the typed progress tool. CLI providers are read-only during intake, so
    they cannot safely write a status file; an HTML comment is the provider-neutral return
    channel. It is untrusted JSON and is normalised/validated before any state transition.
    """
    for match in reversed(list(_INTAKE_PATTERN.finditer(reply or ""))):
        try:
            value = json.loads(match.group(1))
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def strip_intake_markers(reply: str) -> str:
    """Remove the private intake handoff before a reply is saved or displayed."""
    return _INTAKE_PATTERN.sub("", reply or "")


def promote_auto_choice(project: Path, catalog, reply: str = "") -> list[str]:
    """Validate the task-understanding handoff and only then enter PLANNING.

    Model selection alone is deliberately insufficient. The Agent must say the task is ready
    for a meaningful plan; otherwise the natural conversation remains in RESOLVING_KIS while
    it asks the user for the missing scientific fact.
    """
    flow = _flow()
    S = flow.states.State
    ctx = flow.states.FlowContext.load(project)
    if ctx.state is not S.RESOLVING_KIS:
        return list(ctx.selected_kis)
    state = projectrun.load(project)
    marker = _intake_from_reply(reply)
    if marker is not None:
        projectrun.report(project, {
            "status": "working" if marker.get("ready_for_planning") is True else "waiting_for_user",
            "summary": str(marker.get("understanding") or "Understanding the scientific task"),
            "selected_kis": marker.get("selected_kis") or [],
            "intake": marker,
        }, source="agent")
        state = projectrun.load(project)
    intake = state.get("intake") if isinstance(state.get("intake"), dict) else {}
    reported = [str(n) for n in (state.get("selected_kis") or [])]
    known = {ki.name for ki in catalog}
    names = [n for n in reported if n in known]
    # A popup/question and an incomplete or internally inconsistent intake are explicit
    # reasons not to plan yet.  ``ready_for_planning`` is Agent evidence, not authority:
    # the Desktop still checks that the Agent explained the task and did not list an
    # unanswered material question while claiming readiness.
    waiting = setup_flow.request(project)
    if (not names or not str(intake.get("understanding") or "").strip() or
            intake.get("ready_for_planning") is not True or intake.get("missing") or
            (waiting and waiting.get("status") == "waiting")):
        return []
    ctx.selected_kis = names
    ctx.move("kis_resolved", {"selected_kis": names})
    projectrun.select_kis(project, names)
    projectrun.set_stage(project, display_stage(flow, ctx.state), "Planning the run")
    return names
