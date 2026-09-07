"""The API driver: talk to a model directly instead of spawning an agent CLI.

The CLI driver reuses an agent the user has already installed and signed in, so
it needs no key and inherits that agent's tools. This driver is the other half:
an API key, and KISS owns the loop.

Two things follow from owning the loop, and they are the reason to have it:

* **The tools are typed.** The model asks for ``run_preflight`` or
  ``read_ki_file(path)``; it cannot express an arbitrary shell command. The
  permission question changes from "is this command safe" — undecidable from a
  string — to "is this argument in range", which is checkable.
* **It can stop and ask mid-turn.** A one-shot ``claude -p`` exits when the turn
  ends, so a CLI agent can only ask between turns. Here the loop is ours, so a
  request for approval can suspend it and resume on an answer.

No SDK dependency: both wire formats are a single POST of JSON, and taking a
dependency on two vendor SDKs to send one request each would be a poor trade for
a tool meant to install cleanly anywhere.
"""

from __future__ import annotations

import csv
import itertools
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from . import skilllib, tls
from .presentation import activity_marker

TIMEOUT = 300


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    """Stop a timed-out command and every process it started.

    ``Popen.communicate(timeout=...)`` only terminates the direct child when a
    caller reacts with ``proc.kill()``. Build wrappers commonly leave their
    compiler, ``find``, or network helper descendants alive with our output
    pipes still open. Tear down the Windows process tree, or the private
    process group created for this command on POSIX.
    """
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        taskkill = Path(system_root) / "System32" / "taskkill.exe"
        try:
            result = subprocess.run(
                [str(taskkill), "/PID", str(proc.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode:
                proc.kill()
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except OSError:
                pass
        return

    # ``start_new_session=True`` below guarantees that proc.pid is a process
    # group created by us, so killpg cannot target GeoForge's own group.
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # The wrapper may exit before a descendant that ignored SIGTERM. The
    # process group continues to exist until every member is gone, so always
    # issue the final bounded kill and harmlessly ignore a vanished group.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def _run_subprocess_tree(
        command: list[str], *, cwd: str, env: dict[str, str],
        timeout: int) -> subprocess.CompletedProcess[str]:
    """Run one non-interactive command with bounded process-tree cleanup."""
    popen_options = {
        "cwd": cwd,
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "errors": "replace",
    }
    if os.name == "nt":
        # taskkill /T follows the parent/child tree by PID and does not need a
        # console process group. CREATE_NEW_PROCESS_GROUP cannot be combined
        # reliably with CREATE_NO_WINDOW on supported Python/Windows builds.
        popen_options["creationflags"] = getattr(
            subprocess, "CREATE_NO_WINDOW", 0)
    else:
        popen_options["start_new_session"] = True
    proc = subprocess.Popen(command, **popen_options)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired as cleanup_timeout:
            try:
                proc.kill()
            except OSError:
                pass
            # A detached descendant can retain inherited pipe handles even
            # after the direct child is dead. Never turn the timeout handler
            # into another unbounded wait for EOF.
            try:
                stdout, stderr = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired as final_timeout:
                stdout = final_timeout.output or cleanup_timeout.output or ""
                stderr = final_timeout.stderr or cleanup_timeout.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode(errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode(errors="replace")
                stderr += "\nOutput pipes remained open after process-tree cleanup."
        raise subprocess.TimeoutExpired(
            command, timeout, output=stdout, stderr=stderr) from None
    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)


@dataclass
class ApiProvider:
    """One API endpoint and how to authenticate to it."""

    name: str
    label: str
    #: "anthropic" (native messages API) or "openai" (chat/completions shape)
    wire: str
    base_url: str
    env_key: str
    models: dict[str, str] = field(default_factory=dict)
    default_model: str = ""
    signup: str = ""

    def key(self) -> str | None:
        return os.environ.get(self.env_key) or None

    def available(self) -> bool:
        return bool(self.key())


#: Mirrors the provider table the HydroCraft backend already serves, so a key
#: that works there works here.
PROVIDERS: dict[str, ApiProvider] = {
    "anthropic": ApiProvider(
        name="anthropic", label="Claude (API)", wire="anthropic",
        base_url="https://api.anthropic.com/v1/messages",
        env_key="ANTHROPIC_API_KEY",
        models={"claude-sonnet-4-5": "claude-sonnet-4-5",
                "claude-opus-4-1": "claude-opus-4-1"},
        default_model="claude-sonnet-4-5",
        signup="https://console.anthropic.com/settings/keys",
    ),
    "deepseek": ApiProvider(
        name="deepseek", label="DeepSeek (API)", wire="openai",
        base_url="https://api.deepseek.com/chat/completions",
        env_key="DEEPSEEK_API_KEY",
        models={"deepseek-chat": "deepseek-chat",
                "deepseek-reasoner": "deepseek-reasoner"},
        default_model="deepseek-chat",
        signup="https://platform.deepseek.com/api_keys",
    ),
    "openai": ApiProvider(
        name="openai", label="OpenAI (API)", wire="openai",
        base_url="https://api.openai.com/v1/chat/completions",
        env_key="OPENAI_API_KEY",
        models={"gpt-4o": "gpt-4o", "gpt-4o-mini": "gpt-4o-mini"},
        default_model="gpt-4o",
        signup="https://platform.openai.com/api-keys",
    ),
    "openrouter": ApiProvider(
        name="openrouter", label="OpenRouter (API)", wire="openai",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        env_key="OPENROUTER_API_KEY",
        models={"claude-sonnet-4-5": "anthropic/claude-sonnet-4.5",
                "deepseek-chat": "deepseek/deepseek-chat"},
        default_model="deepseek-chat",
        signup="https://openrouter.ai/keys",
    ),
}


def available() -> list[ApiProvider]:
    return [p for p in PROVIDERS.values() if p.available()]


# --- the tools the model may call ------------------------------------------
#
# Deliberately typed and narrow. There is no `bash` here: a KI declares what a
# model needs, so the useful operations are enumerable, and enumerating them is
# what lets the permission layer check an argument instead of guessing at a
# command string.

def tool_schemas(ki, *, setup_mode: bool = False,
                 project_mode: bool = False, flow=None,
                 installation_only: bool = False) -> list[dict]:
    """``flow`` (a flowgate.FlowSession) filters the list by the project's flow state
    (plan v3 B4): the agent never sees a tool it may not call in this state."""
    tools = [
        {
            "name": "read_ki_file",
            "description": (
                "Read a file from this model's Knowledge Infrastructure package "
                "(SKILL.md, dag.yaml, diagnostics/triplets, docs/, tools/). "
                "Always read SKILL.md before proposing how to run the model."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string",
                             "description": "path relative to the KI root, e.g. 'SKILL.md'"},
                    "start_line": {"type": "integer", "minimum": 1,
                                   "description": "first line to return; defaults to 1"},
                    "line_count": {"type": "integer", "minimum": 1, "maximum": 2000,
                                   "description": "maximum lines to return; defaults to 1000"},
                    "ki": {"type": "string",
                           "description": "which selected KI to read (multi-model chats); default: the primary KI"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "list_ki_files",
            "description": "List the files in this KI package, optionally under a subdirectory.",
            "input_schema": {
                "type": "object",
                "properties": {"subdir": {"type": "string"},
                               "ki": {"type": "string",
                                      "description": "which selected KI to list (multi-model chats)"}},
            },
        },
        {
            "name": "run_preflight",
            "description": (
                "Run this KI's preflight_check.py and return its output. This is "
                "the authoritative answer to whether the model is ready to run."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_skills",
            "description": (
                "List the agent skills installed on this machine (name + one-line "
                "description). Skills are reusable instruction packages — use one "
                "when a task matches its description (plotting, statistics, "
                "literature review, document formats, ...)."
            ),
            "input_schema": {"type": "object",
                             "properties": {"query": {"type": "string",
                                            "description": "optional substring filter"}}},
        },
        {
            "name": "read_skill",
            "description": (
                "Read one installed skill's SKILL.md instructions by name. Read it "
                "before applying the skill; follow it like a procedure."
            ),
            "input_schema": {"type": "object",
                             "properties": {"name": {"type": "string"}},
                             "required": ["name"]},
        },
        {
            "name": "search_diagnostics",
            "description": (
                "Search this KI's diagnostics/triplets for an error keyword. Use "
                "this before debugging from first principles — the failure is "
                "often already catalogued with a verified remedy."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"keyword": {"type": "string"}},
                "required": ["keyword"],
            },
        },
    ]
    if project_mode:
        tools += [
            {
                "name": "list_project_files",
                "description": (
                    "List files already present in this chat's local project. "
                    "Inspect these before asking the user to supply data."
                ),
                "input_schema": {"type": "object", "properties": {
                    "subdir": {"type": "string",
                               "description": "relative project directory, normally inputs"},
                }},
            },
            {
                "name": "read_project_file",
                "description": "Read a text file from this chat's local project.",
                "input_schema": {"type": "object", "properties": {
                    "path": {"type": "string"},
                }, "required": ["path"]},
            },
            {
                "name": "write_project_file",
                "description": (
                    "Write a small prepared input, run configuration, provenance "
                    "record, or report inside the chat project. Use the KI's tools "
                    "for generated grids and large scientific files."
                ),
                "input_schema": {"type": "object", "properties": {
                    "path": {"type": "string",
                             "description": "relative path under inputs, runs, outputs, artifacts, or references"},
                    "content": {"type": "string"},
                }, "required": ["path", "content"]},
            },
            {
                "name": "run_ki_tool",
                "description": (
                    "Run one Python preparation tool shipped inside the selected KI. "
                    "Use this for data conversion, grid/soil/weather preparation, "
                    "configuration generation, validation, and model harness steps. "
                    "Arguments may reference this chat project, this KI package, or "
                    "the current KI's GeoForge-managed shared binaries directory. "
                    "Do not replace a KI tool with improvised calculations."
                ),
                "input_schema": {"type": "object", "properties": {
                    "tool_path": {"type": "string",
                                  "description": "Python file relative to the KI root and below a tools/ directory"},
                    "arguments": {"type": "array", "items": {"type": "string"}},
                    "cwd": {"type": "string",
                            "description": "relative project working directory; defaults to project root"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 3600},
                    "ki": {"type": "string",
                           "description": "which selected KI the tool belongs to (multi-model runs); "
                                          "defaults to the chat's primary KI"},
                    "plan_step_id": {"type": "string",
                                     "description": "the approved plan step this run executes "
                                                    "(runs/plan.json steps[].id); required once a "
                                                    "plan is approved — the receipt is bound to it"},
                }, "required": ["tool_path"]},
            },
            {
                "name": "run_calibration",
                "description": (
                    "Run this KI's project calibration adapter through GeoForge's "
                    "bundled calibration engine. numpy, SPOTPY, and pymoo run "
                    "inside the app, not the user's system Python. Use only after "
                    "the real model, observations, adapter, and holdout definition "
                    "are ready. The full report and engine log are saved in the "
                    "chat project's calibration/runs directory."
                ),
                "input_schema": {"type": "object", "properties": {
                    "obs_shape_by_var": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": (
                            "Map every calibration target variable exactly as named "
                            "in calibration.yaml to its dag observation shape."
                        ),
                    },
                    "algorithm": {"type": "string", "enum": [
                        "dds", "sceua", "dream", "nsga2", "nsga3", "moead"]},
                    "budget": {"type": "integer", "minimum": 1, "maximum": 10000},
                    "seed": {"type": "integer"},
                    "determining_metric": {"type": "string"},
                }, "required": ["obs_shape_by_var"]},
            },
            {
                "name": "create_project_plot",
                "description": (
                    "Create a safe line, scatter, or bar plot in this chat's "
                    "artifacts folder. Use a relevant plotting/visualization skill "
                    "to choose an honest chart, then call this tool when the direct "
                    "API has no plotting runtime. GeoForge displays the SVG inline. "
                    "For a project CSV, prefer source_path plus x_column/y_column "
                    "instead of copying every data point through the model."
                ),
                "input_schema": {"type": "object", "properties": {
                    "output_path": {"type": "string",
                                    "description": "relative .svg path below artifacts/"},
                    "kind": {"type": "string", "enum": ["line", "scatter", "bar"]},
                    "title": {"type": "string"},
                    "x_label": {"type": "string"},
                    "y_label": {"type": "string"},
                    "y2_label": {"type": "string",
                                 "description": "optional right-axis label"},
                    "source_path": {"type": "string",
                                    "description": "optional relative .csv file in this chat project"},
                    "x_column": {"type": "string",
                                 "description": "CSV column used for the x axis"},
                    "series": {"type": "array", "items": {"type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "x": {"type": "array", "items": {}},
                            "y": {"type": "array", "items": {"type": "number"}},
                            "y_column": {"type": "string",
                                         "description": "CSV column used for this series"},
                            "axis": {"type": "string", "enum": ["left", "right"],
                                     "description": "use right when units or scale differ from the main series"},
                        }, "required": ["y"]}},
                }, "required": ["output_path", "series"]},
            },
            {
                "name": "publish_project_view",
                "description": (
                    "Publish or update this chat's safe dynamic Project View after "
                    "creating real artifacts. GeoForge renders the declared metrics, "
                    "images, animations, maps, CSV tables, files, and 3D-model "
                    "previews; it never executes model-written HTML or JavaScript. "
                    "Every path must name an existing file below artifacts/."
                ),
                "input_schema": {"type": "object", "properties": {
                    "version": {"type": "integer", "enum": [1]},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "layout": {"type": "string", "enum": ["grid", "single"]},
                    "skills": {"type": "array", "items": {"type": "string"}},
                    "kis": {"type": "array", "items": {"type": "string"}},
                    "panels": {"type": "array", "maxItems": 24, "items": {
                        "type": "object", "properties": {
                            "id": {"type": "string"},
                            "kind": {"type": "string", "enum": [
                                "metric", "image", "animation", "map", "table",
                                "file", "model3d"]},
                            "title": {"type": "string"},
                            "caption": {"type": "string"},
                            "status": {"type": "string"},
                            "value": {},
                            "unit": {"type": "string"},
                            "path": {"type": "string"},
                            "renderer": {"type": "string"},
                        }, "required": ["kind", "title"]}},
                }, "required": ["title", "panels"]},
            },
            {
                "name": "request_user_action",
                "description": (
                    "Pause project preparation and show one concrete action to the "
                    "user. Use only for a protected download, licence/login, private "
                    "data, system permission, or high-impact scientific choice that "
                    "the KI cannot resolve. Never use it for ordinary KI defaults."
                ),
                "input_schema": {"type": "object", "properties": {
                    "kind": {"type": "string", "enum": [
                        "download", "licence", "login", "permission", "choice", "other"]},
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                    "options": {"type": "array", "maxItems": 8, "items": {
                        "type": "object", "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "description": {"type": "string"},
                            "response": {"type": "string",
                                         "description": "exact answer sent back to the agent when selected"},
                        }, "required": ["label"]}},
                    "allow_note": {"type": "boolean"},
                    "url": {"type": "string"},
                    "expected_path": {"type": "string"},
                    "command": {"type": "string"},
                    "resume_hint": {"type": "string"},
                }, "required": ["kind", "title", "message"]},
            },
        ]
    if project_mode or setup_mode:
        tools.append({
            "name": "report_project_progress",
            "description": (
                "Update GeoForge's small project-status display at a meaningful "
                "transition. Report only work actually reached. This records use "
                "of the general KI; it does not create an adaptive KI harness."
            ),
            "input_schema": {"type": "object", "properties": {
                "stage": {"type": "string", "enum": [
                    "understanding", "choosing_ki", "software", "researching",
                    "preparing", "validating", "running", "results"]},
                "status": {"type": "string", "enum": [
                    "idle", "working", "waiting_for_user", "complete", "failed"]},
                "goal": {"type": "string", "description": (
                    "The current modelling goal. Include this only when the user "
                    "has materially replaced or refined the scientific case; do "
                    "not replace it for a simple continue/retry message."
                )},
                "summary": {"type": "string"},
                "selected_kis": {"type": "array", "items": {"type": "string"}},
                "intake": {"type": "object", "description": (
                    "Structured task understanding. GeoForge validates the KI names and will "
                    "enter planning only when ready_for_planning is true."
                ), "properties": {
                    "ready_for_planning": {"type": "boolean"},
                    "understanding": {"type": "string"},
                    "study_area": {"type": "string"},
                    "period": {"type": "string"},
                    "process": {"type": "string"},
                    "scenario": {"type": "string"},
                    "requested_outputs": {"type": "array", "items": {"type": "string"}},
                    "missing": {"type": "array", "items": {"type": "string"}},
                }, "required": ["ready_for_planning", "understanding", "missing"]},
            }, "required": ["stage", "status", "summary"]},
        })
    if setup_mode:
        tools += [
            {
                "name": "run_builtin_setup",
                "description": (
                    "Run GeoForge's bundled setup recipe and return its full step "
                    "report. Use it as a fast first attempt, then diagnose and repair "
                    "the first real failure instead of stopping."
                ),
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_work_files",
                "description": "List files in the writable model setup workspace.",
                "input_schema": {"type": "object", "properties": {
                    "subdir": {"type": "string", "description": "relative workspace path"},
                }},
            },
            {
                "name": "read_work_file",
                "description": (
                    "Read a text file from the writable setup workspace. Use "
                    "start_line/line_count to page through large build files."
                ),
                "input_schema": {"type": "object", "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "minimum": 1},
                    "line_count": {"type": "integer", "minimum": 1,
                                   "maximum": 2000},
                }, "required": ["path"]},
            },
            {
                "name": "write_work_file",
                "description": (
                    "Write a small text file inside the model setup workspace. "
                    "Use this to repair build files or configuration, not to replace "
                    "the scientific model with a surrogate."
                ),
                "input_schema": {"type": "object", "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                }, "required": ["path", "content"]},
            },
            {
                "name": "replace_work_text",
                "description": (
                    "Apply one exact, bounded text replacement inside an "
                    "existing setup-workspace file. Use this for a small "
                    "source/build portability patch when rewriting the whole "
                    "file would be unsafe. The old text must match exactly."
                ),
                "input_schema": {"type": "object", "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string", "minLength": 1},
                    "new": {"type": "string"},
                    "expected_count": {"type": "integer", "minimum": 1,
                                       "maximum": 20},
                }, "required": ["path", "old", "new"]},
            },
            {
                "name": "run_setup_command",
                "description": (
                    "Run one non-shell command inside the model workspace and return "
                    "stdout, stderr, and its exit code. The executable, working "
                    "directory, and explicit path arguments are checked against a "
                    "build-tool/workspace allowlist; sudo, inline Python, credentials, "
                    "and system package installation are intentionally unavailable. "
                    "env.PATH may contain workspace-local toolchain directories; "
                    "GeoForge validates and prepends them to the inherited PATH."
                ),
                "input_schema": {"type": "object", "properties": {
                    "argv": {"type": "array", "items": {"type": "string"},
                             "description": "argument vector, e.g. [\"cmake\",\"-S\",\".\",\"-B\",\"build\"]"},
                    "cwd": {"type": "string", "description": "relative workspace directory"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 3600},
                    "env": {"type": "object", "additionalProperties": {"type": "string"}},
                }, "required": ["argv"]},
            },
            *([{
                "name": "publish_setup_output",
                "description": (
                    "Copy a completed generated output or run directory from the "
                    "model setup workspace into this chat project. Use this after "
                    "a successful setup-mode simulation so full binary/text results "
                    "are preserved in the session without rerunning or encoding them "
                    "through chat."
                ),
                "input_schema": {"type": "object", "properties": {
                    "source": {"type": "string",
                               "description": "relative path below outputs/, runs/, or data/ in the setup workspace"},
                    "destination": {"type": "string",
                                    "description": "relative path below inputs/, runs/, outputs/, artifacts/, or references/ in the chat project"},
                }, "required": ["source", "destination"]},
            }] if project_mode else []),
            {
                "name": "request_user_action",
                "description": (
                    "Pause setup and put one concrete human action on GeoForge's "
                    "Setup page. Use only for a licence, protected download, login, "
                    "system privilege, or scientific choice you cannot resolve."
                ),
                "input_schema": {"type": "object", "properties": {
                    "kind": {"type": "string", "enum": [
                        "download", "licence", "login", "permission", "choice", "other"]},
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                    "options": {"type": "array", "maxItems": 8, "items": {
                        "type": "object", "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "description": {"type": "string"},
                            "response": {"type": "string",
                                         "description": "exact answer sent back to the agent when selected"},
                        }, "required": ["label"]}},
                    "allow_note": {"type": "boolean"},
                    "url": {"type": "string"},
                    "expected_path": {"type": "string"},
                    "command": {"type": "string"},
                    "resume_hint": {"type": "string"},
                }, "required": ["kind", "title", "message"]},
            },
        ]
    if project_mode:
        tools += [
            {
                "name": "write_plan",
                "description": (
                    "PLANNING only. Write runs/plan.json and runs/data-inventory.json (the "
                    "schemas are in your instructions). GeoForge validates them; errors come "
                    "back and nothing is written until they pass. No downloads, no inputs, no "
                    "model runs happen in planning — the user approves the plan first."
                ),
                "input_schema": {"type": "object", "properties": {
                    "plan": {"type": "object"},
                    "data_inventory": {"type": "object"},
                }, "required": ["plan", "data_inventory"]},
            },
            {
                "name": "fetch_data",
                "description": (
                    "EXECUTING only. Download one public http(s) file into inputs/raw/<item_id>/ "
                    "and write a signed download receipt (URL, status, sha256). Use it for every "
                    "download the approved data inventory calls for; a download made any other "
                    "way has no receipt and cannot count."
                ),
                "input_schema": {"type": "object", "properties": {
                    "url": {"type": "string"},
                    "item_id": {"type": "string", "description": "the data-inventory item id"},
                    "filename": {"type": "string"},
                    "plan_step_id": {"type": "string"},
                }, "required": ["url", "item_id"]},
            },
        ]
    # Combined installation + project turns intentionally expose both tool
    # families.  A shared operation such as request_user_action must still be
    # declared only once; the later (setup-aware) definition wins.
    out = list({tool["name"]: tool for tool in tools}.values())
    if installation_only:
        forbidden = {
            "run_preflight", "run_ki_tool", "run_calibration",
            "create_project_plot", "publish_project_view", "fetch_data",
            "publish_setup_output",
        }
        out = [tool for tool in out if tool["name"] not in forbidden]
    if flow is not None:
        allowed = flow.api_tools()
        out = [t for t in out if t["name"] in allowed]
        for tool in out:
            if tool["name"] == "report_project_progress":
                # under the flow the stage is GeoForge's; the agent reports status/summary only
                schema = json.loads(json.dumps(tool["input_schema"]))
                schema["properties"].pop("stage", None)
                schema["required"] = [k for k in schema.get("required", []) if k != "stage"] or ["status", "summary"]
                tool["input_schema"] = schema
                tool["description"] = ("Update GeoForge's project-status display (status + summary; the stage "
                                       "is tracked by GeoForge from the plan, approval and receipts). Report "
                                       "selected_kis when you choose a model.")
    return out


class ToolError(Exception):
    pass


def _safe_relative_file_listing(base: Path, root: Path, limit: int) -> list[str]:
    """List a large agent workspace without failing on one transient path.

    Scientific source trees contain deep generated directories, junctions and
    occasionally paths another build process removes while the agent is
    inspecting them. ``Path.rglob`` aborts the entire tool call on any such
    Windows ``FileNotFoundError``. A directory-listing aid is diagnostic only,
    so skip the unreadable entry and return the bounded evidence collected.
    """
    names: list[str] = []
    for directory, dirs, files in os.walk(
            base, topdown=True, onerror=lambda _error: None,
            followlinks=False):
        dirs.sort()
        for filename in sorted(files):
            try:
                names.append(
                    (Path(directory) / filename).relative_to(root).as_posix())
            except (OSError, ValueError):
                continue
            if len(names) >= limit:
                return sorted(names)
    return sorted(names)


def _read_text_page(path: Path, start_line: object = 1,
                    line_count: object = 1000) -> str:
    """Read a bounded page without forcing agents to invent shell pipelines."""
    try:
        start = int(start_line or 1)
        count = int(line_count or 1000)
    except (TypeError, ValueError) as error:
        raise ToolError("start_line and line_count must be integers") from error
    if start < 1 or count < 1 or count > 2000:
        raise ToolError("start_line must be >= 1 and line_count must be 1..2000")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    return "".join(lines[start - 1:start - 1 + count])[:60000]


_INSTALL_ONLY_PROBE_FLAGS = {"--version", "-V", "-v", "--help", "-h"}
_INSTALL_ONLY_BUILD_NAMES = (
    "build", "compile", "configure", "setup", "install", "bootstrap",
    "quickbuild", "mkmf", "checkout", "external",
)
_INSTALL_ONLY_CODEGEN_NAMES = {
    "bison", "win_bison", "flex", "win_flex", "m4", "swig", "protoc",
    "cython", "f2py",
}
_INSTALL_ONLY_PYTHON_CODEGEN = {
    # RHESSys upstream build generator: committed headers -> one committed
    # build-time C translation unit. It is not a model/data execution path.
    "dynamic_field_lookup.py",
}
_INSTALL_ONLY_LICENSE_ACCEPTANCE = (
    "--accept-license", "--accept-licenses", "--accept-eula",
    "--accept-source-agreements", "--accept-package-agreements",
    "accept_eula", "accept-eula", "eula=accept", "license=accept",
)


def _is_inside(path: Path, root: Path) -> bool:
    """Return whether a resolved path is the root or one of its descendants."""
    return path == root or root in path.parents


def _guard_generated_dependency_shim(path: Path, content: str) -> None:
    """Reject generated modules or packaging that counterfeit dependencies.

    Setup agents may patch an official consumer source tree and rebuild it, but
    must not manufacture a same-named Python module or wheel merely to make an
    import probe green.  Direct site-packages writes are already rejected; this
    also closes the two-step variant where a helper first builds a fake wheel.
    """
    path_text = path.as_posix().lower()
    source = content.lower()
    path_markers = (
        "fcntl_shim", "winfcntl", "build_fcntl", "wurlitzer_shim",
        "install_wurlitzer",
    )
    source_module_markers = (
        "fcntl.py", "winfcntl", "name: fcntl", "name: winfcntl",
        "wurlitzer.py",
    )
    packaging_markers = (
        "site-packages", "dist-packages", "dist-info", ".whl",
        "wheel-version", "metadata-version", "zipfile",
    )
    fake_fcntl_api = (
        re.search(r"(?m)^\s*def\s+fcntl\s*\(", source) is not None and
        "f_getfl" in source
    )
    hand_assembled_wheel = (
        ("zipfile" in source or "tarfile" in source) and
        any(marker in source for marker in (
            ".whl", "dist-info", "wheel-version", "metadata-version",
            "record,"))
    )
    synthetic_binary_setup = (
        path.name.lower() in {"setup.py", "pyproject.toml"} and
        any(marker in source for marker in (".pyd", "*.so", "*.dll")) and
        any(marker in source for marker in (
            "package_data", "data_files", "include_package_data"))
    )
    handwritten_metadata = (
        any(part.lower().endswith(".dist-info") for part in path.parts) or
        (path.name.upper() in {"METADATA", "WHEEL", "RECORD"} and
         "dist-info" in path_text)
    )
    if (hand_assembled_wheel or synthetic_binary_setup or handwritten_metadata):
        raise ToolError(
            "installation agents may not hand-assemble wheels, package "
            "metadata, or a replacement setup project; patch and run the "
            "official source package's build backend instead"
        )
    if (any(marker in path_text for marker in path_markers) or
            fake_fcntl_api or
            (any(marker in source for marker in source_module_markers) and
             any(marker in source for marker in packaging_markers))):
        raise ToolError(
            "installation agents may not generate fcntl/wurlitzer shims or "
            "replacement wheels; patch the official consumer source and "
            "rebuild/install it"
        )


def _guard_local_dependency_shim_wheels(argv: list[str], cwd: Path,
                                        workroot: Path) -> None:
    """Inspect local wheel arguments so a generated shim cannot reach pip."""
    for token in argv[1:]:
        if not token.lower().endswith(".whl"):
            continue
        candidate = Path(token)
        wheel = (candidate.resolve() if candidate.is_absolute()
                 else (cwd / candidate).resolve())
        if (wheel != workroot and workroot not in wheel.parents) or not wheel.is_file():
            continue
        try:
            with zipfile.ZipFile(wheel) as archive:
                members = {name.lower() for name in archive.namelist()}
        except (OSError, zipfile.BadZipFile):
            continue
        if any(
                name == "fcntl.py" or name.endswith("/fcntl.py") or
                name == "wurlitzer.py" or name.endswith("/wurlitzer.py")
                for name in members):
            raise ToolError(
                "installation agents may not install a local wheel that "
                "replaces fcntl or wurlitzer; patch the official consumer "
                "source and rebuild/install it"
            )


def _guard_installation_only_command(argv: list[str], cwd: Path,
                                     workroot: Path) -> None:
    """Enforce the bounded installation command policy.

    This is a defence-in-depth policy aid around the setup allowlist, not an
    operating-system sandbox.  Reject allowlisted programs with known
    child-process escape forms rather than pretending their arguments are
    passive data.
    """
    command = Path(argv[0]).name.lower()
    # Workspace-local Windows tools arrive as absolute ``*.exe`` paths. The
    # policy names the programs, not the platform's executable suffix; without
    # normalising it, staged gcc.exe/gfortran.exe were mistaken for model
    # binaries and restricted to --version/--help.
    command_key = (Path(command).stem if Path(command).suffix.lower() in {
        ".exe", ".cmd", ".bat",
    } else command)
    args = argv[1:]
    resolved_command = Path(argv[0]).resolve()
    in_workspace = _is_inside(resolved_command, workroot)

    joined_args = " ".join(args).lower()
    if any(token in joined_args for token in _INSTALL_ONLY_LICENSE_ACCEPTANCE):
        raise ToolError(
            "installation-only mode cannot accept a licence or EULA on the "
            "user's behalf"
        )

    if command_key == "tar" and any(arg.lower().endswith(".whl") for arg in args):
        raise ToolError(
            "installation agents may not hand-assemble wheel archives; run "
            "the official source package's build backend instead"
        )

    if command_key in {"awk", "find"}:
        raise ToolError(
            f"installation-only mode blocks {command_key}; it can launch arbitrary "
            "child processes. Use a bounded Python inspection probe instead"
        )
    if command_key == "git" and any(arg in {"-c", "--config-env"}
                                 or arg.startswith("--config-env=")
                                 for arg in args):
        raise ToolError(
            "installation-only mode blocks per-command Git configuration "
            "because aliases, pagers, filters and hooks can launch programs"
        )

    # Permit checksum verification from the freshly unpacked portable root,
    # but only for one workspace file. This lets an agent prove the archive's
    # pinned digest without exposing a general workspace executable.
    if command_key in {"sha256sum", "b2sum"}:
        command_parts = tuple(part.lower() for part in resolved_command.parts)
        expected_name = f"{command_key}.exe"
        if (not in_workspace or len(command_parts) < 3 or
                command_parts[-3:] != ("usr", "bin", expected_name)):
            raise ToolError(
                "installation-only checksum utility must be the portable "
                f"workspace MSYS2 usr/bin/{expected_name}"
            )
        if len(args) != 1 or args[0].startswith("-"):
            raise ToolError(
                "portable checksum verification requires exactly one "
                "workspace file"
            )
        candidate = Path(args[0])
        candidate = (candidate.resolve() if candidate.is_absolute()
                     else (cwd / candidate).resolve())
        if not _is_inside(candidate, workroot) or not candidate.is_file():
            raise ToolError("checksum target must be a workspace file")
        return

    # PETSc officially supports the GNU compilers supplied by MSYS2 on
    # Windows. A portable MSYS2 archive is useful for that build, but its
    # package manager must never become a route to the host installation.
    # Only the pacman located at <workspace>/<portable-root>/usr/bin is
    # accepted, and options that redirect its database/root are forbidden.
    if command_key == "pacman":
        expected_tail = ("usr", "bin", "pacman.exe")
        command_parts = tuple(part.lower() for part in resolved_command.parts)
        if (not in_workspace or len(command_parts) < len(expected_tail) or
                command_parts[-3:] != expected_tail):
            raise ToolError(
                "installation-only pacman must be the portable workspace "
                "MSYS2 usr/bin/pacman.exe"
            )
        if len(args) == 1 and args[0] in _INSTALL_ONLY_PROBE_FLAGS:
            return
        blocked_options = {
            "--root", "--sysroot", "--dbpath", "--cachedir", "--gpgdir",
            "--config", "--hookdir", "--logfile", "--nodeps",
            "--noscriptlet", "--overwrite", "--assume-installed", "-u",
            "-r",
        }
        if any(
                token.lower() in blocked_options or
                any(token.lower().startswith(option + "=")
                    for option in blocked_options if option.startswith("--"))
                for token in args):
            raise ToolError(
                "portable pacman may not redirect its root/database, remove "
                "packages, or bypass dependency/script safety"
            )
        operations = [token for token in args if token.startswith("-") and
                      token in {
                          "-Q", "-Qq", "-Qi", "-Qk", "-Ql", "-Qs", "-Qdt",
                          "-Ss", "-Si", "-Sl", "-S", "-Sy", "-Syy", "-Su",
                          "-Syu", "-Syyu",
                      }]
        if len(operations) != 1:
            raise ToolError(
                "portable pacman requires exactly one bounded query or sync "
                "operation"
            )
        operation = operations[0]
        allowed_flags = {
            operation, "--needed", "--noconfirm", "--noprogressbar",
            "--disable-download-timeout", "--downloadonly",
        }
        if any(token.startswith("-") and token not in allowed_flags
               for token in args):
            raise ToolError("portable pacman option is not allowed")
        mutating = operation in {"-S", "-Sy", "-Syy", "-Su", "-Syu", "-Syyu"}
        if mutating and "--noconfirm" not in args:
            raise ToolError(
                "portable pacman mutations require --noconfirm so setup "
                "cannot freeze on an invisible prompt"
            )
        packages = [token for token in args if not token.startswith("-")]
        if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.@-]*", package)
               for package in packages):
            raise ToolError(
                "portable pacman accepts repository package names only, not "
                "URLs or package files"
            )
        return

    # Permit the portable shell only as a script interpreter. Command strings
    # (bash -c/-lc), stdin scripts and script arguments stay blocked; they
    # would erase the path-token and executable policy enforced here.
    if command_key in {"bash", "sh"}:
        expected_name = f"{command_key}.exe"
        command_parts = tuple(part.lower() for part in resolved_command.parts)
        if (not in_workspace or len(command_parts) < 3 or
                command_parts[-3:] != ("usr", "bin", expected_name)):
            raise ToolError(
                "installation-only shell must be the portable workspace "
                f"MSYS2 usr/bin/{expected_name}"
            )
        shell_args = list(args)
        flags = []
        while shell_args and shell_args[0].startswith("-"):
            flags.append(shell_args.pop(0))
        if any(flag not in {"--noprofile", "--norc", "--login", "-l"}
               for flag in flags):
            raise ToolError(
                "portable shell command strings and stdin execution are "
                "blocked; invoke one explicit workspace .sh file"
            )
        if len(shell_args) != 1:
            raise ToolError(
                "portable shell requires exactly one workspace .sh file and "
                "does not accept script arguments"
            )
        script = Path(shell_args[0])
        script = (script.resolve() if script.is_absolute()
                  else (cwd / script).resolve())
        if (not _is_inside(script, workroot) or script.suffix.lower() != ".sh" or
                not script.is_file()):
            raise ToolError(
                "portable shell script must be an existing .sh file inside "
                "the setup workspace"
            )
        try:
            if script.stat().st_size > 250_000:
                raise ToolError("portable shell scripts are limited to 250 KB")
            source = script.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ToolError("portable shell script must be UTF-8 text") from error
        active_source = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#")
        ).lower()
        blocked_commands = (
            "sudo", "runas", "powershell", "pwsh", "cmd", "msiexec",
            "winget", "choco", "wsl", "docker", "reg", "sc", "schtasks",
            "setx", "curl", "wget", "pacman",
        )
        if any(re.search(
                rf"(?m)(?:^|[;&|()]\s*){re.escape(name)}(?:\.exe)?\b",
                active_source) for name in blocked_commands):
            raise ToolError(
                "portable shell script may not invoke host administration, "
                "network download, or package-manager commands"
            )
        if re.search(
                r"(?m)(?:^|[;&|($]\s*)find(?:\.exe)?\s+(?:\.|[\"']\.[\"'])"
                r"(?:\s|$)", active_source):
            raise ToolError(
                "portable shell script may not recursively scan or rewrite a "
                "whole checkout with `find .`; patch only the reported build "
                "files"
            )
        if (re.search(r"(?m)(?:^|[;&|()]\s*)(?:ba|z|k)?sh\s+-[^\n]*c\b",
                      active_source) or
                any(token in active_source
                    for token in _INSTALL_ONLY_LICENSE_ACCEPTANCE) or
                re.search(r"(?:^|[\s'\"])(?:~[/\\]|\.\.[/\\])",
                          active_source)):
            raise ToolError(
                "portable shell script contains a command-string, licence "
                "acceptance, or host/parent path escape"
            )
        # MSYS2 spells a Windows path such as D:\work as /d/work. Translate
        # those explicit drive mounts back before enforcing the same workspace
        # boundary; /mingw64 and /usr are private to the portable MSYS2 root.
        for match in re.finditer(
                r"(?i)(?<![A-Za-z0-9_])/(?:mnt/)?([A-Z])/([^\s'\"]+)",
                source):
            candidate = Path(
                f"{match.group(1)}:/{match.group(2)}").resolve()
            if not _is_inside(candidate, workroot):
                raise ToolError(
                    "portable shell script contains an MSYS drive path "
                    "outside the setup workspace"
                )
        for match in re.finditer(r"(?i)(?<![A-Za-z0-9])([A-Z]:[/\\][^\s'\"]+)",
                                 source):
            candidate = Path(match.group(1)).resolve()
            if not _is_inside(candidate, workroot):
                raise ToolError(
                    "portable shell script contains a Windows path outside "
                    "the setup workspace"
                )
        return

    # Build systems may compile, but their explicit test/run targets would
    # cross from installation into scientific execution.
    if command_key in {
            "make", "gmake", "mingw32-make", "ninja", "meson", "cmake",
            "cargo", "go"}:
        blocked_targets = {"test", "tests", "check", "run", "submit", "example", "examples"}
        if any(arg.lower().lstrip("-") in blocked_targets for arg in args):
            raise ToolError(
                "installation-only mode blocks build-system test/run targets; "
                "compile the software without executing its examples"
            )
        return

    # micromamba is a single-file, workspace-stageable package manager. Keep
    # both its cache/root and environment prefix inside this KI workspace, and
    # do not expose its generic model-execution facility in install-only mode.
    if command_key == "micromamba":
        operations = {arg.lower() for arg in args if not arg.startswith("-")}
        if len(args) == 1 and args[0] in _INSTALL_ONLY_PROBE_FLAGS:
            return
        if "run" in operations or not operations.intersection({
                "create", "install", "update", "list", "info", "search"}):
            raise ToolError(
                "installation-only micromamba may create/install/inspect an "
                "environment but may not run model commands"
            )

        def option_paths(names: set[str]) -> list[Path]:
            found: list[Path] = []
            for index, token in enumerate(args):
                value = ""
                if token in names and index + 1 < len(args):
                    value = args[index + 1]
                elif any(token.startswith(name + "=") for name in names):
                    value = token.split("=", 1)[1]
                if value:
                    candidate = Path(value)
                    found.append(
                        candidate.resolve() if candidate.is_absolute()
                        else (cwd / candidate).resolve())
            return found

        prefixes = option_paths({"-p", "--prefix"})
        roots = option_paths({"-r", "--root-prefix"})
        if operations.intersection({"create", "install", "update"}) and (
                not prefixes or not roots):
            raise ToolError(
                "micromamba create/install/update requires both a workspace "
                "--root-prefix and --prefix"
            )
        for candidate in [*prefixes, *roots]:
            if candidate != workroot and workroot not in candidate.parents:
                raise ToolError("micromamba prefix escapes the setup workspace")
        return

    # Package managers, compilers, source-control and read-only inspection
    # tools are installation operations rather than model invocations.
    if command_key in {
        "git", "pkg-config", "pip", "pip3", "uv", "rustc", "gcc", "g++",
        "clang", "clang++", "gfortran", "tar", "unzip", "curl", "wget",
        "7z", "7za", "7zr", "innoextract", "patch", "sed", "ls", "cp",
        "mv", "ln", "chmod", "ar", "ranlib", "dlltool", "gendef", "nm",
        "objdump", "strip",
        "file", "otool", "xcode-select", "brew",
    }:
        return

    # Source builds legitimately execute generators before compiling. They
    # are neither scientific runs nor example payloads; blocking a staged
    # flex/bison binary made an otherwise complete RHESSys build ask the user
    # for permission that the installation workflow had already granted.
    if command_key in _INSTALL_ONLY_CODEGEN_NAMES:
        return

    # Python is also used for small workspace inspection scripts and package
    # installation.  Do not let a generated script hide a model invocation.
    if command_key.startswith("python"):
        if len(args) == 1 and args[0] in _INSTALL_ONLY_PROBE_FLAGS:
            return
        if len(args) >= 2 and args[0] == "-m" and args[1] in {
                "pip", "ensurepip", "venv", "py_compile", "compileall"}:
            return
        if not args or args[0].startswith("-"):
            raise ToolError(
                "installation-only Python commands must install/compile a package "
                "or run a small workspace inspection script"
            )
        script = Path(args[0])
        script = script.resolve() if script.is_absolute() else (cwd / script).resolve()
        name = script.name.lower()
        try:
            source_text = script.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ToolError(f"cannot inspect installation Python script: {e}") from e
        _guard_generated_dependency_shim(script, source_text)
        if name in _INSTALL_ONLY_PYTHON_CODEGEN:
            return
        if any(word in name for word in _INSTALL_ONLY_BUILD_NAMES):
            return
        if script.parent != workroot or not any(
                word in name for word in ("probe", "inspect", "check", "verify")):
            raise ToolError(
                "installation-only mode blocked this Python model/data command; "
                "only build helpers or root-level inspection probes may run"
            )
        source = source_text.lower()
        if any(token in source for token in (
                "subprocess", "os.system", "os.popen", "popen(", "runpy", "exec(", "eval(")):
            raise ToolError(
                "installation-only inspection probes cannot launch another process; "
                "invoke a permitted build command or use a --help/--version probe directly"
            )
        return

    if in_workspace:
        if any(word in command_key for word in _INSTALL_ONLY_BUILD_NAMES):
            return
        if len(args) == 1 and args[0] in _INSTALL_ONLY_PROBE_FLAGS:
            return
        raise ToolError(
            "installation-only mode blocked a model/example invocation. "
            "A built executable may only be probed with exactly one of "
            "--version, -v, --help, or -h"
        )


def execute_tool(name: str, args: dict, ki, cfg, *, setup_mode: bool = False,
                 setup_context: dict | None = None,
                 project_mode: bool = False, flow=None) -> str:
    """Run one tool. Every path argument is confined to the KI package.

    ``flow`` (flowgate.FlowSession, plan v3 B4): when present, every call is re-checked
    against the project's flow state before it runs (the schema filter is not trusted on
    its own), writes obey ``flow.write_allowed``, model/tool runs and downloads write
    signed receipts, and agent progress reports cannot move the stage."""
    if flow is not None:
        from .flowgate import FlowDenied
        try:
            flow.check_tool(name)
        except FlowDenied as e:
            raise ToolError(str(e)) from None
    root = Path(ki.root).resolve()
    workroot = Path(cfg.root).resolve()
    provider_id = str((setup_context or {}).get("provider_id") or "")
    # During a direct-API installation turn the model setup workspace and the
    # chat project are deliberately separate.  Keep both roots explicit so an
    # agent can finish installation and then run/publish into the chat project
    # without weakening the setup command sandbox.
    project_root = Path(
        (setup_context or {}).get("project_root") or workroot
    ).resolve()
    progress_root = project_root
    if (bool((setup_context or {}).get("installation_only")) and name in {
            "run_preflight", "run_ki_tool", "run_calibration",
            "create_project_plot", "publish_project_view", "fetch_data",
            "publish_setup_output"}):
        raise ToolError(
            f"{name} is unavailable during an installation-only test; use "
            "only a cheap executable startup or declared import probe"
        )

    # A chat owns its scenario files, but the scientific software is installed
    # once in the current KI's managed workspace.  That binary role is a narrow
    # capability granted by GeoForge's config; it is not an arbitrary external
    # filesystem permission.  KI tools may read/execute it directly without
    # making the user copy large model installs into every chat project.
    project_argument_roots = [project_root, workroot, root]
    binary_role = (getattr(cfg, "roles", {}) or {}).get("binaries")
    if binary_role:
        binary_root = Path(binary_role).expanduser().resolve()
        if binary_root not in project_argument_roots:
            project_argument_roots.append(binary_root)

    def _inside(rel: str) -> Path:
        if Path(rel).is_absolute():
            raise ToolError(f"absolute paths are not accepted: {rel}")
        # Resolve then verify containment: a bare prefix check is defeated by
        # '..' and by symlinks, and this is the only place model-supplied paths
        # reach the filesystem.
        p = (root / rel).resolve()
        if p != root and root not in p.parents:
            raise ToolError(f"path escapes the KI package: {rel}")
        return p

    def _inside_work(rel: str) -> Path:
        if Path(rel).is_absolute():
            raise ToolError(f"absolute workspace paths are not accepted: {rel}")
        p = (workroot / rel).resolve()
        if p != workroot and workroot not in p.parents:
            raise ToolError(f"path escapes the setup workspace: {rel}")
        return p

    def _inside_project(rel: str) -> Path:
        if Path(rel).is_absolute():
            raise ToolError(f"absolute project paths are not accepted: {rel}")
        p = (project_root / rel).resolve()
        if p != project_root and project_root not in p.parents:
            raise ToolError(f"path escapes the chat project: {rel}")
        return p

    def _ki_scoped(rel: str) -> tuple[Path, Path]:
        """(path, ki_root) for read/list tools — another SELECTED KI may be named (kimi desktop
        review #1: multi-KI chats must reach every selected KI through the typed tools)."""
        ki_root = root
        if flow is not None and args.get("ki"):
            from .flowgate import FlowDenied
            try:
                _n, ki_root = flow.ki_root_for(args.get("ki"), root)
            except FlowDenied as e:
                raise ToolError(str(e)) from None
            ki_root = Path(ki_root).resolve()
        if Path(rel).is_absolute():
            raise ToolError(f"absolute paths are not accepted: {rel}")
        p = (ki_root / rel).resolve()
        if p != ki_root and ki_root not in p.parents:
            raise ToolError(f"path escapes the KI package: {rel}")
        return p, ki_root

    if name == "read_ki_file":
        p, _r = _ki_scoped(args.get("path", ""))
        if not p.is_file():
            raise ToolError(f"no such file in this KI: {args.get('path')}")
        return _read_text_page(
            p, args.get("start_line", 1), args.get("line_count", 1000))

    if name == "list_ki_files":
        base, ki_root = _ki_scoped(args.get("subdir") or ".")
        names = _safe_relative_file_listing(base, ki_root, 400)
        return "\n".join(names) or "(empty)"

    if name == "run_preflight":
        from . import install as _install
        step = _install.run_preflight(ki, cfg.python, cfg)
        return f"{'PASS' if step.ok else 'FAIL'}\n{step.detail}"

    if name == "search_diagnostics":
        kw = (args.get("keyword") or "").lower()
        if not kw:
            raise ToolError("keyword required")
        hits: list[str] = []
        for f in root.rglob("*"):
            if not f.is_file() or "diagnostic" not in str(f.relative_to(root)):
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if kw in line.lower():
                    hits.append(
                        f"{f.relative_to(root).as_posix()}:{i}: {line.strip()[:200]}")
        return "\n".join(hits[:40]) or f"no diagnostics mention {kw!r}"

    if name in ("list_skills", "read_skill"):
        if name == "list_skills":
            q = (args.get("query") or "").lower()
            found = [item for item in skilllib.discover()
                     if not q or q in item["name"].lower()
                     or q in item["description"].lower()]
            return ("\n".join(f"{item['name']} — {item['description']}"
                              for item in found[:200]) or "no skills installed")
        try:
            return skilllib.read(args.get("name", ""))[:60000]
        except FileNotFoundError:
            raise ToolError(f"no skill named {args.get('name')!r}")

    if project_mode and name == "list_project_files":
        base = _inside_project(args.get("subdir") or ".")
        if not base.is_dir():
            raise ToolError(f"no such project directory: {args.get('subdir')}")
        names = []
        for f in sorted(base.rglob("*")):
            if not f.is_file() or "memory" in f.relative_to(project_root).parts:
                continue
            try:
                names.append(
                    f"{f.relative_to(project_root).as_posix()} "
                    f"({f.stat().st_size} bytes)")
            except OSError:
                continue
        return "\n".join(names[:1000]) or "(no project files yet)"

    if project_mode and name == "read_project_file":
        p = _inside_project(args.get("path") or "")
        if not p.is_file():
            raise ToolError(f"no such project file: {args.get('path')}")
        if p.stat().st_size > 5_000_000:
            raise ToolError("project file is too large for the text reader; use a KI tool")
        return p.read_text(encoding="utf-8", errors="replace")[:120000]

    if project_mode and name == "write_project_file":
        p = _inside_project(args.get("path") or "")
        content = args.get("content")
        if not isinstance(content, str):
            raise ToolError("content must be text")
        if len(content.encode("utf-8")) > 1_000_000:
            raise ToolError("write_project_file is limited to 1 MB; use a KI tool")
        rel = p.relative_to(project_root)
        writable = {"inputs", "runs", "outputs", "artifacts", "references"}
        calibration_write = (len(rel.parts) >= 2 and rel.parts[0] == "calibration"
                             and rel.parts[1] in {"cases", "kis"})
        if not rel.parts or (rel.parts[0] not in writable and not calibration_write):
            raise ToolError(
                "project writes must stay under inputs, runs, outputs, artifacts, "
                "references, calibration/cases, or calibration/kis")
        if flow is not None and not flow.write_allowed(p):
            # plan v3 B4: approval.json, flow-state.json, .geoforge/, the plan files outside
            # PLANNING, and anything under runs/ except logs/notes are never agent-writable
            raise ToolError(f"writing {rel.as_posix()} is not allowed in state "
                            f"{flow.state.value} (protected or outside the writable subtrees)")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        # Tool results are consumed by agents on every host. Keep project paths
        # in the API's portable slash form instead of leaking Windows `\\`
        # separators that are frequently copied into later JSON/tool calls.
        return f"wrote {rel.as_posix()} ({len(content.encode('utf-8'))} bytes)"

    if project_mode and name == "run_ki_tool":
        tool_ki_name, tool_root = getattr(ki, "name", root.name), root
        if flow is not None:
            from .flowgate import FlowDenied
            try:
                tool_ki_name, tool_root = flow.ki_root_for(args.get("ki"), root)
            except FlowDenied as e:
                raise ToolError(str(e)) from None
            tool_root = Path(tool_root).resolve()
            if tool_root != root and tool_root not in project_argument_roots:
                project_argument_roots.append(tool_root)
        def _inside_tool_ki(rel: str, _root=tool_root) -> Path:
            # same containment rule as _inside, against the KI this call names (multi-KI runs)
            if Path(rel).is_absolute():
                raise ToolError(f"absolute paths are not accepted: {rel}")
            p = (_root / rel).resolve()
            if p != _root and _root not in p.parents:
                raise ToolError(f"path escapes the KI package: {rel}")
            return p
        script = _inside_tool_ki(args.get("tool_path") or "")
        try:
            rel_script = script.relative_to(tool_root)
        except ValueError:
            raise ToolError("tool escapes the selected KI")
        from ki_tools_common.flow.tools import is_ki_tool
        if script.suffix.casefold() != ".py" or not is_ki_tool(tool_root, script):
            raise ToolError("run_ki_tool accepts only shipped Python files below tools/")
        arguments = args.get("arguments") or []
        if (not isinstance(arguments, list) or len(arguments) > 100 or
                not all(isinstance(x, str) and len(x) <= 4000 for x in arguments)):
            raise ToolError("arguments must be a list of short strings")
        cwd = _inside_project(args.get("cwd") or ".")
        if not cwd.is_dir():
            raise ToolError(f"project directory does not exist: {args.get('cwd')}")
        for token in arguments:
            value = token.split("=", 1)[1] if token.startswith("-") and "=" in token else token
            if not (value.startswith(("/", "./", "../")) or
                    "/" in value or "\\" in value):
                continue
            candidate = Path(value)
            resolved = candidate.resolve() if candidate.is_absolute() else (cwd / candidate).resolve()
            if not any(
                    resolved == base or base in resolved.parents
                    for base in project_argument_roots):
                raise ToolError(f"tool argument path escapes the project and KI: {value}")
        timeout = max(1, min(int(args.get("timeout_seconds") or 600), 3600))
        child_env = {
            key: value for key, value in os.environ.items()
            if not any(secret in key.upper() for secret in (
                "API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))
        }
        child_env["KISS_ROOT"] = str(project_root)
        from .paths import with_ki_tools_common
        child_env = with_ki_tools_common(cfg, child_env)
        from .calibration import with_framework_env
        child_env = with_framework_env(child_env)
        if provider_id:
            from .settings import with_provider_proxy
            child_env = with_provider_proxy(provider_id, child_env)
        command = [str(cfg.python), str(script), *arguments]
        before = None
        if flow is not None:
            from . import flowgate as _fg
            from .flowgate import FlowDenied
            # the step, its KI and its tool are checked BEFORE anything runs (codex R2 #4)
            try:
                flow.check_step_tool(args.get("plan_step_id"), tool_ki_name, script)
            except FlowDenied as e:
                raise ToolError(str(e)) from None
            before = _fg._snapshot(project_root)
        started = time.time()
        try:
            proc = _run_subprocess_tree(
                command, cwd=str(cwd), env=child_env, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            tail = ((e.stdout or "") + (e.stderr or ""))[-12000:]
            if flow is not None:
                try:
                    flow.record_tool_run(ki=tool_ki_name, ki_root=tool_root, command=command, cwd=cwd,
                                         started_at=started, finished_at=time.time(), exit_code=None,
                                         before=before, plan_step_id=args.get("plan_step_id"),
                                         stdout_tail=tail)
                except Exception as exc:  # the timeout is the headline; the receipt failure is noted
                    tail += f"\n[receipt not written: {exc}]"
            return f"TIMEOUT after {timeout}s\n{tail}"
        finished = time.time()
        output = (proc.stdout + proc.stderr)[-80000:]
        if flow is None:
            return f"exit_code={proc.returncode}\n{output}"
        from .flowgate import FlowDenied
        try:
            summary = flow.record_tool_run(ki=tool_ki_name, ki_root=tool_root, command=command, cwd=cwd,
                                           started_at=started, finished_at=finished,
                                           exit_code=proc.returncode, before=before,
                                           plan_step_id=args.get("plan_step_id"),
                                           stdout_tail=output[-20000:])
        except FlowDenied as e:
            raise ToolError(str(e)) from None
        return (f"exit_code={proc.returncode}\n[RECEIPT] {json.dumps(summary, ensure_ascii=False)}\n"
                f"{output}")

    if project_mode and name == "run_calibration":
        from . import calibration as _calibration
        calib_before = None
        calib_started = time.time()
        if flow is not None:
            from . import flowgate as _fg
            from .flowgate import FlowDenied
            try:
                flow.check_step_tool(args.get("plan_step_id"), getattr(ki, "name", root.name), None)
            except FlowDenied as e:
                raise ToolError(str(e)) from None
            calib_before = _fg._snapshot(project_root, subs=("inputs", "outputs", "artifacts", "calibration"))
        # Ensure the adapter copy exists before building the generated runtime
        # KI. `ki` is already the session-materialised package in pinned chats.
        _calibration.ensure_project(project_root, [ki])
        try:
            result = _calibration.run_project(
                project=project_root,
                ki_name=ki.name,
                ki_path=root,
                obs_shape_by_var=args.get("obs_shape_by_var") or {},
                algorithm=args.get("algorithm") or None,
                budget=args.get("budget"),
                seed=int(args.get("seed") or 0),
                determining_metric=args.get("determining_metric") or None,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ToolError(str(exc)) from None
        report = result.get("report") if isinstance(result.get("report"), dict) else {}
        summary = {
            "run_id": result.get("run_id"),
            "status": report.get("status"),
            "promotable": report.get("promotable"),
            "backend": report.get("backend"),
            "best_loss": report.get("best_loss"),
            "best_params": report.get("best_params"),
            "reason": report.get("reason"),
            "report_path": result.get("report_path"),
            "log_path": result.get("log_path"),
            "log_tail": result.get("log_tail"),
        }
        if flow is not None:
            from .flowgate import FlowDenied
            try:
                _kname = getattr(ki, "name", root.name)
                summary["receipt"] = flow.record_tool_run(
                    ki=_kname, ki_root=root,
                    command=["geoforge-calibration", _kname, str(args.get("algorithm") or "default")],
                    cwd=project_root, started_at=calib_started, finished_at=time.time(),
                    exit_code=0 if str(report.get("status") or "").lower() in ("ok", "success", "completed", "done") else 1,
                    before=calib_before, plan_step_id=args.get("plan_step_id"),
                    stdout_tail=str(result.get("log_tail") or ""))
            except FlowDenied as e:
                raise ToolError(str(e)) from None
        return json.dumps(summary, indent=2, ensure_ascii=False, default=str)

    if project_mode and name == "write_plan":
        if flow is None:
            raise ToolError("write_plan is available only in a flow-managed project")
        plan_doc, inv_doc = args.get("plan"), args.get("data_inventory")
        if not isinstance(plan_doc, dict) or not isinstance(inv_doc, dict):
            raise ToolError("plan and data_inventory must be JSON objects")
        errs = flow.write_plan(plan_doc, inv_doc)
        if errs:
            return "PLAN NOT WRITTEN — fix these and call write_plan again:\n- " + "\n- ".join(errs[:30])
        return ("Plan files written: runs/plan.json, runs/data-inventory.json. Stop here: GeoForge "
                "shows the plan to the user; execution starts in a separate session after approval.")

    if project_mode and name == "fetch_data":
        if flow is None:
            raise ToolError("fetch_data is available only in a flow-managed project")
        from .flowgate import FlowDenied
        try:
            info = flow.fetch(str(args.get("url") or ""), str(args.get("item_id") or ""),
                              filename=args.get("filename"), plan_step_id=args.get("plan_step_id"))
        except FlowDenied as e:
            raise ToolError(str(e)) from None
        except (OSError, ValueError) as e:
            raise ToolError(f"download failed: {e}") from None
        return "[RECEIPT] " + json.dumps(info, ensure_ascii=False)

    if project_mode and name == "create_project_plot":
        from .plotting import PlotError, render_svg
        p = _inside_project(args.get("output_path") or "")
        rel = p.relative_to(project_root)
        if not rel.parts or rel.parts[0] != "artifacts" or p.suffix.lower() != ".svg":
            raise ToolError("plot output_path must be a .svg file below artifacts/")
        plot_args = dict(args)
        if args.get("source_path"):
            source = _inside_project(args.get("source_path") or "")
            if not source.is_file() or source.suffix.lower() != ".csv":
                raise ToolError("plot source_path must be a project CSV file")
            if source.stat().st_size > 20_000_000:
                raise ToolError("plot CSV is larger than 20 MB")
            x_column = str(args.get("x_column") or "")
            requested = args.get("series") or []
            if not x_column or not requested or not all(
                    isinstance(item, dict) and item.get("y_column")
                    for item in requested):
                raise ToolError("CSV plots require x_column and y_column for every series")
            with source.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
            if not rows:
                raise ToolError("plot CSV has no data rows")
            columns = set(rows[0])
            y_columns = [str(item["y_column"]) for item in requested]
            missing = [column for column in [x_column, *y_columns]
                       if column not in columns]
            if missing:
                raise ToolError(f"plot CSV is missing columns: {', '.join(missing)}")
            # Keep the request and SVG bounded while preserving both endpoints.
            max_rows = max(2, 5000 // len(requested))
            if len(rows) > max_rows:
                indices = sorted({round(i * (len(rows) - 1) / (max_rows - 1))
                                  for i in range(max_rows)})
                rows = [rows[i] for i in indices]
            built_series = []
            for item, y_column in zip(requested, y_columns):
                built_series.append({
                    "name": item.get("name") or y_column,
                    "axis": item.get("axis") or "left",
                    "x": [row[x_column] for row in rows],
                    "y": [row[y_column] for row in rows],
                })
            plot_args["series"] = built_series
        try:
            summary = render_svg(plot_args, p)
        except (OSError, PlotError) as e:
            raise ToolError(str(e)) from None
        return (f"{summary}\nInclude it in the reply as: "
                f"![{args.get('title') or p.stem}]({rel.as_posix()})")

    if project_mode and name == "publish_project_view":
        from . import projectview as _projectview
        try:
            state = _projectview.publish(project_root, args, source="direct_api")
        except (OSError, TypeError, ValueError) as exc:
            raise ToolError(str(exc)) from None
        return ("Project View published. GeoForge will render it for this chat.\n" +
                json.dumps({
                    "title": state["title"],
                    "panels": len(state["panels"]),
                    "path": "artifacts/project-view.json",
                }, indent=2, ensure_ascii=False))

    if project_mode and not setup_mode and name == "request_user_action":
        from . import projectrun as _projectrun, setup as _setup
        doc = _setup.request_user(project_root, args)
        _projectrun.report(progress_root, {
            "status": "waiting_for_user", "summary": doc["title"],
            "blocker": doc,
        }, source="api_handoff")
        return "GeoForge will show this one request to the user:\n" + json.dumps(doc, indent=2)

    if (project_mode or setup_mode) and name == "report_project_progress":
        from . import projectrun as _projectrun
        payload = dict(args or {})
        if flow is not None and "stage" in payload:
            payload.pop("stage")        # plan v3 B5: the flow owns the stage; agents report status/summary
        state = _projectrun.report(progress_root, payload, source="api")
        note = "" if flow is None else "\n(the stage is tracked by GeoForge from the plan/approval/receipts; only status and summary were taken from your report)"
        return "Project status updated:\n" + json.dumps(state, indent=2) + note

    if setup_mode and name == "run_builtin_setup":
        callback = (setup_context or {}).get("run_builtin")
        if not callable(callback):
            raise ToolError("the built-in setup runner is unavailable")
        return str(callback())[-60000:]

    if setup_mode and name == "list_work_files":
        base = _inside_work(args.get("subdir") or ".")
        if not base.is_dir():
            raise ToolError(f"no such workspace directory: {args.get('subdir')}")
        names = _safe_relative_file_listing(base, workroot, 800)
        return "\n".join(names) or "(empty)"

    if setup_mode and name == "read_work_file":
        p = _inside_work(args.get("path") or "")
        if not p.is_file():
            raise ToolError(f"no such workspace file: {args.get('path')}")
        return _read_text_page(
            p, args.get("start_line", 1), args.get("line_count", 1000))

    if setup_mode and name == "write_work_file":
        p = _inside_work(args.get("path") or "")
        relative_parts = {part.lower() for part in p.relative_to(workroot).parts}
        if (bool((setup_context or {}).get("installation_only")) and
                p.parent == workroot and p.name in {
                    "status.json", "installation-test.json",
                    ".geoforge-install.json",
                }):
            raise ToolError(
                f"{p.name} is GeoForge-owned verification state and cannot "
                "be written by the installation agent"
            )
        if (bool((setup_context or {}).get("installation_only")) and
                relative_parts.intersection({"site-packages", "dist-packages"})):
            raise ToolError(
                "installation agents may not write directly into site-packages; "
                "patch the official workspace source and rebuild/install it"
            )
        content = args.get("content")
        if not isinstance(content, str):
            raise ToolError("content must be text")
        if bool((setup_context or {}).get("installation_only")):
            _guard_generated_dependency_shim(p, content)
        if len(content.encode("utf-8")) > 250_000:
            raise ToolError("write_work_file is limited to 250 KB")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return (
            f"wrote {p.relative_to(workroot).as_posix()} "
            f"({len(content.encode('utf-8'))} bytes)"
        )

    if setup_mode and name == "replace_work_text":
        p = _inside_work(args.get("path") or "")
        if not p.is_file():
            raise ToolError(f"no such workspace file: {args.get('path')}")
        relative_parts = {part.lower() for part in p.relative_to(workroot).parts}
        if (bool((setup_context or {}).get("installation_only")) and
                p.parent == workroot and p.name in {
                    "status.json", "installation-test.json",
                    ".geoforge-install.json",
                }):
            raise ToolError(
                f"{p.name} is GeoForge-owned verification state and cannot "
                "be written by the installation agent"
            )
        if (bool((setup_context or {}).get("installation_only")) and
                relative_parts.intersection({"site-packages", "dist-packages"})):
            raise ToolError(
                "installation agents may not patch site-packages in place; "
                "patch the official workspace source and rebuild/install it"
            )
        old, new = args.get("old"), args.get("new")
        if (not isinstance(old, str) or not old or
                not isinstance(new, str)):
            raise ToolError("old must be non-empty text and new must be text")
        try:
            expected = int(args.get("expected_count", 1))
        except (TypeError, ValueError) as error:
            raise ToolError("expected_count must be an integer") from error
        if expected < 1 or expected > 20:
            raise ToolError("expected_count must be 1..20")
        if len(old.encode("utf-8")) > 100_000 or len(new.encode("utf-8")) > 100_000:
            raise ToolError("replacement text is limited to 100 KB")
        raw = p.read_bytes()
        if len(raw) > 5_000_000:
            raise ToolError("replace_work_text is limited to files under 5 MB")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ToolError("replace_work_text requires a UTF-8 text file") from error
        actual = text.count(old)
        if actual != expected:
            raise ToolError(
                f"expected {expected} exact match(es), found {actual}; "
                "read the relevant page and retry with more context"
            )
        updated = text.replace(old, new, expected)
        p.write_text(updated, encoding="utf-8", newline="")
        return (
            f"replaced {expected} exact match(es) in "
            f"{p.relative_to(workroot).as_posix()}"
        )

    if setup_mode and name == "run_setup_command":
        argv = args.get("argv")
        if (not isinstance(argv, list) or not argv or len(argv) > 100 or
                not all(isinstance(x, str) and x and len(x) <= 4000 for x in argv)):
            raise ToolError("argv must be a non-empty list of short strings")
        executable = argv[0]
        allowed = {
            "git", "cmake", "make", "gmake", "mingw32-make", "ninja",
            "meson", "pkg-config", "micromamba",
            "python", "python3", "pip", "pip3", "uv", "cargo", "rustc", "go",
            "gcc", "g++", "clang", "clang++", "gfortran", "tar", "unzip",
            "7z", "7za", "7zr", "innoextract", "curl", "wget", "patch",
            "sed", "awk", "find", "ls", "cp", "mv", "ln", "ar", "ranlib",
            "dlltool", "gendef", "nm", "objdump", "strip",
            "chmod", "file", "otool", "xcode-select", "brew", "bison", "flex",
            "win_bison", "win_flex", "m4", "swig", "protoc", "cython", "f2py",
        }
        exe_path = Path(executable)
        executable_name = exe_path.name.lower()
        executable_key = (
            Path(executable_name).stem
            if Path(executable_name).suffix.lower() in {".exe", ".cmd", ".bat"}
            else executable_name
        )
        external_roots = []
        for raw in (setup_context or {}).get("existing_roots") or []:
            try:
                candidate = Path(str(raw)).expanduser().resolve(strict=False)
            except (OSError, RuntimeError):
                continue
            external_roots.append(candidate.parent if candidate.is_file() else candidate)
        # ``Path.is_absolute`` alone does not distinguish a Windows relative
        # executable (``binaries\\tools\\python.exe``) from a bare command.
        # Treat both native separators as paths before consulting the command
        # allowlist; otherwise a real workspace-local toolchain is rejected as
        # an unknown command exactly when the setup agent tries to use it.
        if exe_path.is_absolute() or "/" in executable or "\\" in executable:
            resolved = (workroot / exe_path).resolve() if not exe_path.is_absolute() else exe_path.resolve()
            cfg_python = Path(cfg.python).resolve()
            permitted_roots = [workroot, root,
                               Path(cfg.roles.get("binaries", workroot)).resolve(),
                               *external_roots]
            if resolved != cfg_python and not any(
                    resolved == base or base in resolved.parents for base in permitted_roots):
                raise ToolError(f"executable is outside the setup workspace: {executable}")
            if (os.name == "nt" and resolved.suffix.lower() == ".exe" and
                    resolved.is_file()):
                try:
                    with resolved.open("rb") as executable_file:
                        pe_header = executable_file.read(2)
                except OSError as error:
                    raise ToolError(
                        f"cannot inspect Windows executable: {error}") from error
                if pe_header != b"MZ":
                    raise ToolError(
                        f"{resolved.name} is not a Windows PE executable (missing "
                        "MZ header); if the download endpoint returned an archive, "
                        "extract the real executable before running it"
                    )
            argv[0] = str(resolved)
        elif executable_key not in allowed:
            raise ToolError(f"command is not in the setup allowlist: {executable}")
        if executable_key == "brew" and len(argv) > 1 and argv[1] not in (
                "--prefix", "--version", "list", "info", "config"):
            raise ToolError("Homebrew changes require the user; create a permission request")

        cwd = _inside_work(args.get("cwd") or ".")
        if not cwd.is_dir():
            raise ToolError(f"command directory does not exist: {args.get('cwd')}")
        if bool((setup_context or {}).get("installation_only")):
            _guard_installation_only_command(argv, cwd, workroot)
            _guard_local_dependency_shim_wheels(argv, cwd, workroot)
        # Reject path arguments that escape the workspace. This is not a
        # shell, but programs such as cp, curl and git still accept output
        # paths of their own. Compiler/system include flags are allowed only
        # for the conventional read-only roots they genuinely need.
        readable_system_roots = tuple(Path(p) for p in (
            "/usr", "/opt/homebrew", "/Library/Frameworks",
        ))

        def check_path_token(token: str) -> None:
            value = token.split("=", 1)[1] if token.startswith("-") and "=" in token else token
            if value.startswith(("http://", "https://", "git@")):
                return
            if not (value.startswith(("/", "./", "../")) or
                    "/" in value or "\\" in value):
                return
            candidate = Path(value)
            resolved = candidate.resolve() if candidate.is_absolute() else (cwd / candidate).resolve()
            allowed_workspace = any(
                resolved == base or base in resolved.parents
                for base in (workroot, root,
                             Path(cfg.roles.get("binaries", workroot)).resolve(),
                             *external_roots)
            )
            allowed_system = any(
                resolved == base or base in resolved.parents for base in readable_system_roots)
            if not allowed_workspace and not allowed_system:
                raise ToolError(f"command path escapes the setup workspace: {value}")

        for token in argv[1:]:
            check_path_token(token)
        if Path(argv[0]).name in ("python", "python3") or Path(argv[0]).resolve() == Path(cfg.python).resolve():
            if "-c" in argv:
                raise ToolError("inline Python is unavailable; write a workspace script and run it")
        timeout = max(1, min(int(args.get("timeout_seconds") or 300), 3600))
        # Some scientific executables ignore conventional --help/--version
        # flags and immediately enter their normal blocking input loop.  A
        # startup probe is only a load/response check, so never let one make
        # the Setup UI appear frozen for the normal five-minute command limit.
        if (bool((setup_context or {}).get("installation_only")) and
                len(argv) == 2 and argv[1] in _INSTALL_ONLY_PROBE_FLAGS):
            timeout = min(timeout, 20)
        extra_env = args.get("env") or {}
        if not isinstance(extra_env, dict):
            raise ToolError("env must be an object")
        safe_env = {}
        path_prefix: list[str] = []
        banned = {"HOME", "SHELL", "DYLD_INSERT_LIBRARIES", "PYTHONPATH"}
        workspace_path_env = {
            "CONDA_PKGS_DIRS", "CONDA_ENVS_DIRS", "MAMBA_ROOT_PREFIX",
            "CONDA_PREFIX", "CONDARC", "MAMBARC", "MSYS2_ROOT",
            "PETSC_DIR", "TMP", "TEMP", "TMPDIR",
        }
        for key, value in extra_env.items():
            if (not re.fullmatch(r"[A-Z_][A-Z0-9_]{0,63}", str(key)) or
                    key in banned or not isinstance(value, str) or len(value) > 8000):
                raise ToolError(f"unsafe environment override: {key}")
            if key == "PATH":
                for entry in value.split(os.pathsep):
                    if not entry:
                        continue
                    candidate = Path(entry)
                    resolved = (candidate.resolve() if candidate.is_absolute()
                                else (cwd / candidate).resolve())
                    if not any(
                            resolved == base or base in resolved.parents
                            for base in (workroot, root,
                                         Path(cfg.roles.get(
                                             "binaries", workroot)).resolve(),
                                         *external_roots)):
                        raise ToolError(
                            f"PATH entry escapes the setup workspace: {entry}")
                    path_prefix.append(str(resolved))
                continue
            if key in workspace_path_env:
                for entry in value.split(os.pathsep):
                    if not entry:
                        continue
                    candidate = Path(entry)
                    resolved = (candidate.resolve() if candidate.is_absolute()
                                else (cwd / candidate).resolve())
                    if resolved != workroot and workroot not in resolved.parents:
                        raise ToolError(
                            f"environment path escapes the setup workspace: "
                            f"{key}={entry}")
            safe_env[key] = value
        # A tool or build script must never inherit the API key that is driving
        # the agent. Keep the normal build environment, remove credentials.
        child_env = {
            key: value for key, value in os.environ.items()
            if not any(secret in key.upper() for secret in (
                "API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))
        }
        from .paths import with_ki_tools_common
        child_env = with_ki_tools_common(cfg, child_env)
        if provider_id:
            from .settings import with_provider_proxy
            child_env = with_provider_proxy(provider_id, child_env)
        command_path = Path(argv[0]).resolve()
        if (os.name == "nt" and command_path.name.lower() == "pacman.exe"
                and workroot in command_path.parents
                and tuple(part.lower() for part in command_path.parts[-3:])
                    == ("usr", "bin", "pacman.exe")):
            # Portable pacman's post-install hooks need its own sh/coreutils.
            # A GUI-launched parent need not have any MSYS2 tools on PATH.
            path_prefix.insert(0, str(command_path.parent))
        if path_prefix:
            safe_env["PATH"] = os.pathsep.join(
                [*path_prefix, child_env.get("PATH", "")])
        try:
            proc = _run_subprocess_tree(
                argv, cwd=str(cwd), env={**child_env, **safe_env},
                timeout=timeout)
        except subprocess.TimeoutExpired as e:
            tail = ((e.stdout or "") + (e.stderr or ""))[-12000:]
            return f"TIMEOUT after {timeout}s\n{tail}"
        except OSError as e:
            # A non-executable script, missing command, or platform launch
            # error is normal repair-loop evidence.  Let the model see it and
            # choose another invocation (usually ``python3 script.py``)
            # instead of aborting the entire API turn.
            return f"FAILED_TO_START: {type(e).__name__}: {e}"
        output = (proc.stdout + proc.stderr)[-50000:]
        return f"exit_code={proc.returncode}\n{output}"

    if setup_mode and project_mode and name == "publish_setup_output":
        source = _inside_work(args.get("source") or "")
        destination = _inside_project(args.get("destination") or "")
        if not source.exists():
            raise ToolError(f"no such generated setup output: {args.get('source')}")
        source_rel = source.relative_to(workroot)
        destination_rel = destination.relative_to(project_root)
        if not source_rel.parts or source_rel.parts[0] not in {"outputs", "runs", "data"}:
            raise ToolError("published setup files must come from outputs, runs, or data")
        writable = {"inputs", "runs", "outputs", "artifacts", "references"}
        if not destination_rel.parts or destination_rel.parts[0] not in writable:
            raise ToolError("published files must stay in a project data folder")

        candidates = [source] if source.is_file() else list(source.rglob("*"))
        # A scientific run directory commonly links its executable and shared
        # model tables back into the same setup workspace.  Those links are
        # safe to publish as normal files when their targets remain inside the
        # workspace.  Keeping the links themselves would make the chat project
        # non-portable, while rejecting them prevented an otherwise successful
        # run from being archived at all.
        files: list[tuple[Path, Path]] = []
        link_count = 0
        for item in candidates:
            if item.is_symlink():
                try:
                    resolved = item.resolve(strict=True)
                except OSError as e:
                    raise ToolError(f"generated output contains a broken symbolic link: {item.name}") from e
                if resolved != workroot and workroot not in resolved.parents:
                    raise ToolError(
                        f"generated output link escapes the setup workspace: {item.name}")
                if not resolved.is_file():
                    raise ToolError(
                        f"generated output contains a symbolic directory: {item.name}")
                files.append((item, resolved))
                link_count += 1
            elif item.is_file():
                files.append((item, item))
        if len(files) > 2000:
            raise ToolError("generated output contains more than 2,000 files")
        total = sum(copy_source.stat().st_size for _, copy_source in files)
        if total > 512 * 1024 * 1024:
            raise ToolError("generated output is larger than the 512 MB publish limit")
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(files[0][1], destination)
        else:
            destination.mkdir(parents=True, exist_ok=True)
            for item, copy_source in files:
                target = destination / item.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(copy_source, target)
        link_note = (f", {link_count} internal links copied as files"
                     if link_count else "")
        return (
            f"published {source_rel.as_posix()} to {destination_rel.as_posix()} "
            f"({len(files)} files, {total} bytes{link_note})"
        )

    if setup_mode and name == "request_user_action":
        from . import projectrun as _projectrun, setup as _setup
        doc = _setup.request_user(workroot, args)
        _projectrun.report(progress_root, {
            "stage": "software", "status": "waiting_for_user",
            "summary": doc["title"], "blocker": doc,
        }, source="api_handoff")
        return "GeoForge is now waiting for the user:\n" + json.dumps(doc, indent=2)

    raise ToolError(f"unknown tool {name}")


# --- wire formats -----------------------------------------------------------

def _post(url: str, headers: dict, payload: dict, *, provider: str) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        from .settings import proxy_url_for
        proxy = proxy_url_for(provider)
        handlers = [
            urllib.request.ProxyHandler(
                {"http": proxy, "https": proxy} if proxy else {}),
            urllib.request.HTTPSHandler(context=tls.context()),
        ]
        with urllib.request.build_opener(*handlers).open(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:800]
        raise ToolError(f"HTTP {e.code} from {url}: {body}") from None
    except urllib.error.URLError as e:
        raise ToolError(f"cannot reach {url}: {e.reason}") from None


def _cacheable_system(system: str) -> list[dict]:
    """The instruction block as one cacheable prefix.

    Tools and system render ahead of messages, so a single breakpoint here
    covers both. It matters more than one call per turn suggests: the agent
    loop below runs up to ``max_steps`` times for a single user message, and
    without this the same ~20KB KI catalogue was re-sent, and re-billed at full
    price, on every one of them.
    """
    return [{"type": "text", "text": system,
             "cache_control": {"type": "ephemeral"}}]


def _cached_messages(messages: list[dict]) -> list[dict]:
    """Messages with a rolling cache breakpoint on the newest turn.

    Each loop step resends the entire conversation. Marking the tail lets the
    next step read everything up to here from cache rather than paying for it
    again. Copied rather than mutated — ``messages`` is reused across steps and
    a breakpoint left behind on an old turn would pin the cache to stale text.
    """
    if not messages:
        return messages
    content = messages[-1].get("content")
    if isinstance(content, str):
        blocks: list = [{"type": "text", "text": content}]
    elif isinstance(content, list) and content:
        blocks = [dict(b) if isinstance(b, dict) else b for b in content]
    else:
        return messages
    if not isinstance(blocks[-1], dict):
        return messages
    blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return [*messages[:-1], {**messages[-1], "content": blocks}]


def _anthropic_turn(prov, model, system, messages, tools, key):
    data = _post(prov.base_url,
                 {"x-api-key": key, "anthropic-version": "2023-06-01"},
                 {"model": model, "max_tokens": 4096,
                  "system": _cacheable_system(system),
                  "messages": _cached_messages(messages), "tools": tools},
                 provider=f"api:{getattr(prov, 'name', 'anthropic')}")
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    calls = [(b["id"], b["name"], b.get("input") or {})
             for b in data.get("content", []) if b.get("type") == "tool_use"]
    return text, calls, data.get("content", [])


def _openai_turn(prov, model, system, messages, tools, key):
    oai_tools = [{"type": "function",
                  "function": {"name": t["name"], "description": t["description"],
                               "parameters": t["input_schema"]}} for t in tools]
    msgs = [{"role": "system", "content": system}, *messages]
    data = _post(prov.base_url, {"Authorization": f"Bearer {key}"},
                 {"model": model, "messages": msgs, "tools": oai_tools},
                 provider=f"api:{getattr(prov, 'name', 'openai')}")
    choice = (data.get("choices") or [{}])[0].get("message", {})
    text = choice.get("content") or ""
    calls = []
    for c in (choice.get("tool_calls") or []):
        # Preserve a valid call id/name even when the vendor truncates only
        # the JSON arguments.  Feeding a normal tool error back under that id
        # lets the model retry on the next step instead of dropping the whole
        # turn.  Missing structural fields still fail closed below.
        try:
            call_id = c["id"]
            function = c["function"]
            name = function["name"]
            raw_args = function.get("arguments") or "{}"
        except (KeyError, TypeError) as e:
            raise ToolError(f"vendor returned a malformed tool call: {e}") from None
        try:
            args = json.loads(raw_args)
            if not isinstance(args, dict):
                args = {}
        except json.JSONDecodeError as e:
            args = {
                "_vendor_argument_error": f"invalid JSON arguments: {e}",
                "_raw_arguments": str(raw_args)[:2000],
            }
        calls.append((call_id, name, args))
    return text, calls, choice


_TEXT_TOOL_REQUEST = re.compile(
    r"\[\[GEOF_TOOL:[A-Za-z0-9_.-]+\]\]|"
    r"<invoke\s+name=[\"'][A-Za-z0-9_.-]+[\"'][^>]*>[\s\S]*?<parameter\b",
    re.I,
)


def _looks_like_text_tool_request(text: str) -> bool:
    """Detect providers printing tool syntax instead of making a tool call.

    Some OpenAI-compatible endpoints occasionally return an XML-like tool
    request in ``content`` with an empty structured ``tool_calls`` array. It
    must not be shown as if work happened: no tool was actually run.
    """
    return bool(_TEXT_TOOL_REQUEST.search(str(text or "")))


def run(prov: ApiProvider, ki, cfg, system: str, task: str,
        *, model: str | None = None, max_steps: int | None = None,
        history: list[dict] | None = None,
        approve: Callable[[str, dict], bool] | None = None,
        setup_mode: bool = False,
        setup_context: dict | None = None,
        project_mode: bool = False,
        presentation: str = "chat",
        flow=None) -> Iterator[str]:
    """Drive one task to completion, yielding text as it is produced.

    ``approve`` is the seam the CLI driver cannot offer: it is called before
    each tool runs and may refuse. Returning False denies that one call and
    tells the model why, rather than aborting the turn.
    """
    if flow is not None:
        flow.provider_succeeded = False
    key = prov.key()
    if not key:
        yield f"[{prov.label}: set {prov.env_key} — get one at {prov.signup}]"
        return

    want = model or prov.default_model
    if prov.models and want not in prov.models and want not in prov.models.values():
        yield (f"[{prov.label} does not offer {want!r}; choose from "
               f"{list(prov.models)}]")
        return
    model_id = prov.models.get(want, want)
    tool_context = dict(setup_context or {})
    tool_context.setdefault("provider_id", f"api:{prov.name}")
    tools = tool_schemas(
        ki, setup_mode=setup_mode, project_mode=project_mode, flow=flow,
        installation_only=bool(tool_context.get("installation_only")),
    )
    # Prior turns travel as REAL messages, not flattened into one user blob
    # with USER:/YOU: markers — the vendor's own multi-turn handling is the
    # thing that makes context work, and counterfeit markers cannot exist in a
    # role field.
    messages: list[dict] = []
    for m in history or []:
        role = "assistant" if m.get("role") == "assistant" else "user"
        body = str(m.get("text", ""))[:8000]
        if body:
            messages.append({"role": role, "content": body})
    messages.append({"role": "user", "content": task})
    text_tool_retries = 0

    steps = range(max_steps) if max_steps is not None else itertools.count()
    for step in steps:
        try:
            if prov.wire == "anthropic":
                text, calls, raw = _anthropic_turn(prov, model_id, system, messages, tools, key)
            else:
                text, calls, raw = _openai_turn(prov, model_id, system, messages, tools, key)
        except ToolError as e:
            yield f"\n[{prov.label} failed: {e}]"
            return

        if not calls and _looks_like_text_tool_request(text):
            # Do not leak provider-specific pseudo XML into chat, and do not
            # pretend it ran. Give the model one clean chance to use the typed
            # tools that were already sent with the request.
            if text_tool_retries:
                yield (f"\n[{prov.label} returned a tool request as plain text. "
                       "Nothing in that request was run. Retry this message or "
                       "switch the AI connection.]\n")
                return
            text_tool_retries += 1
            if prov.wire == "anthropic":
                messages.append({"role": "assistant", "content": raw})
            else:
                messages.append(raw)
            messages.append({
                "role": "user",
                "content": ("Your previous response printed internal tool-call "
                            "markup as ordinary text, so no action ran. Use the "
                            "provided structured function tools now. Do not print "
                            "XML, <invoke>, or GEOF_TOOL markers."),
            })
            continue

        # A response which also invokes tools is normally scratch narration
        # ("Let me inspect...", "Now I will..."). Keep it in the provider's
        # internal history, but reserve the visible answer for the final
        # no-tool response. Forensic setup pages can still request log mode.
        if text and (not calls or presentation == "log"):
            yield text
        if not calls:
            if flow is not None:
                flow.provider_succeeded = True
            return

        results = []
        for call_id, name, args in calls:
            if presentation == "log":
                yield f"\n`> {name}({', '.join(f'{k}={v!r}' for k, v in args.items())[:80]})`\n"
            else:
                yield activity_marker(name)
            if approve is not None and not approve(name, args):
                out = "DENIED by the user. Do not retry; explain what you needed it for."
            else:
                try:
                    out = execute_tool(name, args, ki, cfg, setup_mode=setup_mode,
                                       setup_context=tool_context,
                                       project_mode=project_mode, flow=flow)
                except ToolError as e:
                    out = f"ERROR: {e}"
            results.append((call_id, out))

        if prov.wire == "anthropic":
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": cid, "content": out}
                for cid, out in results]})
        else:
            messages.append(raw)
            for cid, out in results:
                messages.append({"role": "tool", "tool_call_id": cid, "content": out})

    if max_steps is not None:
        yield f"\n[stopped after {max_steps} steps without finishing]"
