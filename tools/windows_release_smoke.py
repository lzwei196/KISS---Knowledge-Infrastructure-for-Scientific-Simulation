"""Check a Windows bundle outside the checkout, without keys or model installs.

Run this against both the portable bundle and the silent install destination.
It uses the frozen executable for HTTP, harness and calibration import checks;
the host Python only drives the checks. It does not exercise paid AI providers.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

import yaml


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       capture_output=True, timeout=20,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        process.wait(timeout=20)


def check(bundle: Path, report: dict) -> None:
    if os.name != "nt":
        raise RuntimeError("Run this release check on Windows")
    executable = bundle / "GeoForge Desktop.exe"
    internal = bundle / "_internal"
    for path in (executable, internal / "python311.dll",
                 internal / "release-manifest.json"):
        if not path.is_file():
            raise AssertionError(f"Required release file missing: {path}")
    manifest = json.loads((internal / "release-manifest.json").read_text("utf-8"))
    report["version"] = manifest["version"]
    packages = sorted(p for p in (internal / "models").iterdir() if p.is_dir())
    assert len(packages) == 127, f"Expected 127 KI directories, got {len(packages)}"
    assert all((p / "SKILL.md").is_file() for p in packages)
    assert all((p / "docs" / "install.windows.md").is_file() for p in packages)
    recipes = [p for p in packages if (p / "kiss.windows.yaml").is_file()]
    assert len(recipes) == 23, f"Expected 23 Windows recipes, got {len(recipes)}"
    for package in recipes:
        embedded = yaml.safe_load((package / "kiss.windows.yaml").read_text("utf-8"))
        shared = yaml.safe_load((internal / "kiss" / "manifests" /
                                 f"{package.name}.yaml").read_text("utf-8"))
        assert embedded == shared, f"Conflicting recipe copies: {package.name}"
    report.update(ki_count=len(packages), windows_notes=len(packages),
                  windows_recipes=len(recipes), python_dll="python311.dll")
    with tempfile.TemporaryDirectory(prefix="geoforge-release-smoke-") as temporary:
        isolated = Path(temporary)
        env = os.environ.copy()
        for key in list(env):
            if key.endswith("_API_KEY") or key in ("PYTHONPATH", "PYTHONHOME",
                                                  "GEOFORGE_KI_UPDATE_BRANCH"):
                env.pop(key, None)
        env.update(APPDATA=str(isolated / "roaming"),
                   LOCALAPPDATA=str(isolated / "local"),
                   GEOFORGE_KI_UPDATE_HOME=str(isolated / "ki-updates"))
        # Never pass --models: discovery must use the bundled library.
        for command in ("harness-status", "calibration-status"):
            process = subprocess.Popen([str(executable), command], cwd=isolated,
                                       env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                code = process.wait(timeout=120)
                assert code == 0, f"Frozen {command} exited {code}"
                report[command] = "passed"
            finally:
                stop(process)
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            port = available.getsockname()[1]
        process = subprocess.Popen(
            [str(executable), "gui", "--no-browser", "--desktop-server",
             "-p", str(port), "-w", str(isolated / "work")],
            cwd=isolated, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def fetch(route: str) -> str:
            with opener.open(f"http://127.0.0.1:{port}{route}", timeout=45) as response:
                assert response.status == 200, route
                return response.read().decode("utf-8")

        try:
            deadline = time.monotonic() + 90
            while True:
                assert process.poll() is None, "Frozen HTTP server exited during startup"
                try:
                    assert "GeoForge" in fetch("/")
                    break
                except (OSError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise RuntimeError("Frozen HTTP server did not start in 90 seconds")
                    time.sleep(0.5)
            routes = ["/", "/setup", "/library", "/i18n.js", "/clipboard.js"]
            for route in routes:
                assert len(fetch(route)) > 100, f"Empty asset: {route}"
            models = json.loads(fetch("/api/models"))
            assert {m["name"] for m in models} == {p.name for p in packages}
            assert "KI HARNESS v1" in fetch("/api/prompt/MODFLOW6")
            flow = json.loads(fetch("/api/flow-status"))
            assert flow.get("ready"), flow
            assert "_internal" in flow["source"], flow
            updates = json.loads(fetch("/api/ki-updates"))
            assert updates["branch"] == "main", updates
            report.update(http_routes=routes + ["/api/models", "/api/prompt/MODFLOW6",
                          "/api/flow-status", "/api/ki-updates"],
                          flow="passed", ki_update_branch=updates["branch"])
        finally:
            stop(process)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = {"bundle": str(args.bundle.resolve()), "passed": False}
    try:
        check(args.bundle.resolve(), report)
        report["passed"] = True
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
