#!/usr/bin/env python3
"""Re-sync the bundled KI harness from the server copy, through port.substitute().

The desktop ships its own copy of ki_tools_common/harness/ki_harness.py. The only
legitimate difference from the server file is the relocatable PROJECT_PY default
(`KISSPATH_PYTHON_ENV/bin/python`), which `kiss_cli.port.substitute` produces.
Anything else is drift (the 2026-08-27 revert bccfa5a dropped the edit mode, the
outputs block and the obligations registry by hand-restoring an old copy).

    python kiss/scripts/sync_harness.py [--server PATH] [--check]

--check exits 1 when the bundled file differs from the ported server file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
BUNDLED = REPO / "ki_tools_common" / "ki_tools_common" / "harness" / "ki_harness.py"
DEFAULT_SERVER = Path("/mnt/disk1/Hydrocraft_server/models/ki_tools_common/ki_tools_common/harness/ki_harness.py")


def ported(server_text: str) -> str:
    sys.path.insert(0, str(REPO / "kiss"))
    from kiss_cli import port
    text, _n = port.substitute(server_text)
    leaks = [l for l in text.splitlines() if "/mnt/disk1" in l or "/home/server" in l]
    if leaks:
        raise SystemExit("server-only paths survived substitution:\n  " + "\n  ".join(leaks))
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not a.server.is_file():
        print(f"server harness not found: {a.server}", file=sys.stderr)
        return 2
    new = ported(a.server.read_text(encoding="utf-8"))
    old = BUNDLED.read_text(encoding="utf-8") if BUNDLED.is_file() else ""
    if a.check:
        if new == old:
            print("bundled harness is in sync with the server copy")
            return 0
        print("DRIFT: bundled harness differs from the ported server copy", file=sys.stderr)
        return 1
    BUNDLED.write_text(new, encoding="utf-8")
    print(f"wrote {BUNDLED} ({len(new.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
