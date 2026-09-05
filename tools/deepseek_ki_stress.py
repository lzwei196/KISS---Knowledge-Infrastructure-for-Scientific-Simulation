#!/usr/bin/env python3
"""Resumable, sequential DeepSeek setup stress test for every bundled KI."""

from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import csv
import json
import os
from pathlib import Path
import shutil
import stat
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener


OPENER = build_opener(HTTPCookieProcessor(CookieJar()))


def http_json(url: str, payload: dict | None = None, timeout: float = 30) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Server:
    def __init__(self, repo: Path, workroot: Path):
        self.repo, self.workroot = repo, workroot
        self.proc: subprocess.Popen | None = None
        self.base = ""

    def start(self) -> None:
        port = free_port()
        self.base = f"http://127.0.0.1:{port}"
        log = self.workroot.parent / "server.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        stream = log.open("ab")
        cmd = [sys.executable, str(self.repo / "kiss" / "kiss_entry.py"),
               "gui", "--no-browser", "--port", str(port),
               "--workroot", str(self.workroot)]
        self.proc = subprocess.Popen(cmd, cwd=self.repo / "kiss", stdout=stream,
                                     stderr=subprocess.STDOUT)
        deadline = time.time() + 30
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"GeoForge server exited with {self.proc.returncode}; see {log}")
            try:
                http_json(self.base + "/api/models", timeout=2)
                return
            except (OSError, ValueError):
                time.sleep(.25)
        self.stop()
        raise TimeoutError("GeoForge server did not become ready in 30 seconds")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(5)
        self.proc = None


def run_setup(base: str, model: str, timeout_seconds: int) -> tuple[str, str]:
    result: list[tuple[str, str]] = []

    def request() -> None:
        try:
            req = Request(base + "/api/setup-agent",
                          data=json.dumps({"model": model, "provider": "api:deepseek",
                                           "llm_model": "deepseek-chat",
                                           "installation_only": True}).encode(),
                          headers={"Content-Type": "application/json"})
            with OPENER.open(req, timeout=300) as response:
                body = response.read().decode("utf-8", "replace")
            result.append(("completed", body[-8000:]))
        except Exception as exc:  # recorded per KI; the matrix continues
            result.append(("request-error", repr(exc)))

    thread = threading.Thread(target=request, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    return ("timeout", f"wall-clock timeout after {timeout_seconds}s") if thread.is_alive() else result[0]


def classify(state: dict, transport: str, installation: dict | None = None) -> str:
    software = state.get("software") or {}
    request = state.get("request") or {}
    if installation and installation.get("usable"):
        return "installed"
    if request.get("status") == "waiting":
        return "needs-user"
    if transport == "timeout":
        return "timeout"
    return "failed"


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ["model", "result", "seconds", "software_state", "request_kind", "error", "finished_at"]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("_stress_deepseek_windows_20260827"))
    parser.add_argument("--timeout-minutes", type=int, default=60)
    parser.add_argument("--limit", type=int, help="smoke-test only the first N pending KIs")
    parser.add_argument("--models", nargs="+",
                        help="run only these KI names (useful for targeted regressions)")
    parser.add_argument("--cleanup", action="store_true",
                        help="remove each dedicated install after its result is safely recorded")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root = args.root.resolve(); workroot = root / "installs"
    root.mkdir(parents=True, exist_ok=True); workroot.mkdir(exist_ok=True)
    jsonl, csv_path = root / "results.jsonl", root / "results.csv"
    rows = []
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try: rows.append(json.loads(line))
            except ValueError: pass
    done = {row["model"] for row in rows}
    server = Server(repo, workroot)
    try:
        server.start()
        models = [item["name"] for item in http_json(server.base + "/api/models")]
        (root / "models.json").write_text(json.dumps(models, indent=2), encoding="utf-8")
        if len(models) != 127:
            raise RuntimeError(f"expected 127 bundled KIs, API returned {len(models)}")
        pending = [name for name in models if name not in done]
        if args.models:
            requested = set(args.models)
            unknown = requested.difference(models)
            if unknown:
                raise ValueError("unknown KI names: " + ", ".join(sorted(unknown)))
            pending = [name for name in pending if name in requested]
        if args.limit is not None: pending = pending[:args.limit]
        print(f"DeepSeek KI stress: {len(done)}/127 recorded; running {len(pending)}", flush=True)
        for index, model in enumerate(pending, len(done) + 1):
            started = time.time(); target = workroot / model
            print(f"[{index}/127] {model}: setup starting", flush=True)
            try:
                http_json(server.base + "/api/setup-location", {"model": model, "path": str(target)})
                transport, detail = run_setup(server.base, model, args.timeout_minutes * 60)
                if transport == "timeout":
                    server.stop(); server.start()
                state = http_json(server.base + "/api/setup/" + quote(model), timeout=30)
                installation_path = target / "installation-test.json"
                installation = (json.loads(installation_path.read_text(encoding="utf-8"))
                                if installation_path.is_file() else None)
                software, request = state.get("software") or {}, state.get("request") or {}
                primary = software.get("primary_error") or {}
                error = ((installation or {}).get("summary") or
                         (primary.get("detail") if isinstance(primary, dict)
                          else str(primary or detail)))
                row = {"model": model, "result": classify(state, transport, installation),
                       "seconds": round(time.time() - started, 1),
                       "software_state": ((installation or {}).get("state") or
                                          software.get("state", "")),
                       "request_kind": request.get("kind", ""), "error": (error or detail)[-2000:],
                       "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            except Exception as exc:
                row = {"model": model, "result": "harness-error",
                       "seconds": round(time.time() - started, 1), "software_state": "",
                       "request_kind": "", "error": repr(exc),
                       "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
                # One model or one spawned installer must not invalidate every
                # later KI. A dead/refusing backend is infrastructure damage,
                # so restore it before recording and continuing the matrix.
                try:
                    server.stop()
                    server.start()
                except Exception as restart_exc:
                    row["error"] += f"; server restart failed: {restart_exc!r}"
            with jsonl.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row); write_csv(csv_path, rows)
            print(f"[{index}/127] {model}: {row['result']} ({row['seconds']}s)", flush=True)
            if args.cleanup:
                resolved = target.resolve(strict=False)
                if resolved.parent != workroot.resolve():
                    raise RuntimeError(f"refusing cleanup outside stress workroot: {resolved}")
                def _remove_readonly(func, path, exc_info):
                    """Retry files made read-only by Windows installers/build tools."""
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except OSError:
                        raise exc_info[1]

                shutil.rmtree(resolved, onerror=_remove_readonly)
                if resolved.exists():
                    raise RuntimeError(f"cleanup did not remove stress workspace: {resolved}")
        return 0
    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
