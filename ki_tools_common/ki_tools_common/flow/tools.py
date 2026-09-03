"""Declared KI entrypoints, shared by planning and execution checks.

Older KIs use s1_grid/, s2_forcing/, etc. Those scripts are accepted only
when the package's own protocol names them; arbitrary project scripts,
preflights and symlink escapes are never promoted to executable plan tools.
"""
from pathlib import Path
import os
import re


def is_ki_tool(root: Path, tool: Path | str) -> bool:
    try:
        return _is_ki_tool(root, tool)
    except (OSError, ValueError, RuntimeError, TypeError):
        # Malformed paths, unreadable protocols and symlink cycles fail closed.
        return False


def _is_ki_tool(root: Path, tool: Path | str) -> bool:
    root = Path(root).resolve()
    p = Path(tool)
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()
    if root not in p.parents or not p.is_file() or p.name in ("preflight_check.py", "__init__.py"):
        return False
    if not (p.suffix.lower() in (".py", ".sh") or (not p.suffix and os.access(p, os.X_OK))):
        return False
    rel = p.relative_to(root).as_posix()
    if rel.startswith("tools/"):
        return True
    if not re.match(r"s[0-9]+_[A-Za-z0-9_-]+/", rel):
        return False
    for name in ("SKILL.md", "SKILL_en.md", "dag.yaml", "knowledge_infrastructure.yaml"):
        doc = root / name
        if doc.is_file() and not doc.is_symlink():
            text = doc.read_text(encoding="utf-8", errors="replace")
            if re.search(r"(?<![A-Za-z0-9_./-])" + re.escape(rel) + r"(?![A-Za-z0-9_./-])", text):
                return True
    return False
