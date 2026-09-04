#!/usr/bin/env python3
"""Copy the planner's data from the server's ata-kdt tree into flow/data (desktop build step).

    python -m ki_tools_common.flow.build_data [--source /mnt/disk1/Hydrocraft_server/ata-kdt] [--dest <flow/data>]

Copies ONLY what plan.derive() reads: cards/*_ata_card.yaml, couplings/coupling_config_*.yaml
and couple_*.py, forcing_providers/*.yaml, obtain_maps/_schema.md, artifacts/coupling_matrix_v2.yaml.
Run outputs never come along. Prints a manifest with sha256 per file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(source: Path, dest: Path) -> dict:
    spec = {
        "cards": ("cards", "*_ata_card.yaml"),
        "couplings": ("couplings", "coupling_config_*.yaml"),
        "couplings_py": ("couplings", "couple_*.py"),
        "forcing_providers": ("forcing_providers", "*.yaml"),
    }
    manifest: dict[str, str] = {}
    for sub, pattern in spec.values():
        src = source / sub
        out = dest / sub
        out.mkdir(parents=True, exist_ok=True)
        for f in sorted(src.glob(pattern)):
            shutil.copy2(f, out / f.name)
            manifest[f"{sub}/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
    for rel in ("obtain_maps/_schema.md", "artifacts/coupling_matrix_v2.yaml"):
        f = source / rel
        if f.is_file():
            target = dest / Path(rel).name
            shutil.copy2(f, target)
            manifest[Path(rel).name] = hashlib.sha256(f.read_bytes()).hexdigest()
    (dest / "MANIFEST.json").write_text(json.dumps({"source": str(source), "files": manifest},
                                                   indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=Path("/mnt/disk1/Hydrocraft_server/ata-kdt"))
    ap.add_argument("--dest", type=Path, default=HERE / "data")
    a = ap.parse_args()
    if not (a.source / "cards").is_dir():
        print(f"no ata-kdt cards under {a.source}", file=sys.stderr)
        return 2
    m = build(a.source, a.dest)
    print(f"copied {len(m)} files to {a.dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
