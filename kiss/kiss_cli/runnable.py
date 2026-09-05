"""Is this model actually runnable? — code, not opinion.

``preflight_check.py`` answers "is the file there": ``check_file(...,
executable=True)`` tests existence and the x bit and nothing else. A binary
built for another architecture, or missing libnetcdf / libgfortran / an MPI
runtime, passes that check and fails the moment anyone tries to use it. A
Python model whose numpy is absent passes it too.

This module closes that gap with four escalating tests, all mechanical:

  1. present   — the executable exists where the KI says it does
  2. shaped    — it is the right kind of executable for this machine
                 (ELF vs Mach-O vs PE vs script, and the right architecture)
  3. linked    — everything it needs resolves: shared libraries for a compiled
                 binary, imports for a script. Same question, two runtimes.
  4. responds  — it actually executes

Only (4) proves usability; (2) and (3) explain nearly every failure of it.
The agent does not judge any of this — it reads the verdict and acts.
"""

from __future__ import annotations

import ast
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: Flags that make a model print something and exit rather than start solving.
#: Tried in order; a model that ignores all of them still counts as running if
#: it exits on its own.
PROBE_FLAGS = ("--version", "-v", "--help", "-h", "")

#: Interpreters for models shipped as source. A scientific model written in
#: Python is no less installed than one written in Fortran; it just fails
#: differently, so it has to be probed differently.
INTERPRETERS = {
    # The frozen app's sys.executable is the GeoForge launcher, not Python.
    # ``check`` replaces this with the selected model/runtime interpreter.
    ".py": ["python3"],
    ".R": ["Rscript"], ".r": ["Rscript"],
    ".jl": ["julia"],
    ".sh": ["bash"], ".bash": ["bash"],
    ".m": ["octave", "--no-gui", "--eval"],
    ".pl": ["perl"],
}

_MARK = "@@KISS-MISSING@@"

_IMPORT_RE = re.compile(r"^\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)", re.M)

#: A process can start, print one of these, and exit — having proved only that
#: the *launcher* works. APSIM's binary loads and links cleanly, then reports
#: "You must install .NET"; the model cannot run. Treating that as success is
#: the exact false green this module exists to prevent.
MISSING_RUNTIME = (
    ("must install .net", "the .NET runtime is not installed"),
    ("dotnet: not found", "the .NET runtime is not installed"),
    ("no java runtime", "no Java runtime is installed"),
    ("unable to locate a java runtime", "no Java runtime is installed"),
    ("jvmlib", "no Java runtime is installed"),
    ("error while loading shared libraries", "a shared library is missing"),
    ("image not found", "a shared library is missing"),
    ("modulenotfounderror", "a Python module is missing"),
    ("importerror", "a Python import failed"),
    ("command not found", "a required command is not on PATH"),
    ("no such file or directory", "an interpreter or helper is missing"),
)


def _runtime_gap(out: str) -> str:
    """Name the missing runtime a probe just reported, if it reported one."""
    low = out.lower()
    for needle, why in MISSING_RUNTIME:
        if needle in low:
            return why
    return ""

#: Languages whose models are compiled: these must have a binary to be usable,
#: whatever their preflight remembered to declare. Judging a Fortran model on
#: imports alone would pass it while its executable is missing entirely.
COMPILED = {"fortran", "c", "c++", "cpp", "csharp", "julia", "matlab",
            "c++/c/python", "c/c++"}

#: Modules that ship with CPython — absent from site-packages by design, so
#: never report them missing.
_STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}


@dataclass
class Verdict:
    """What we found out, in the order we found it out."""

    model: str
    binary: str = ""
    present: bool = False
    shaped: bool = False
    linked: bool = False
    responds: bool = False
    kind: str = ""
    missing: list[str] = field(default_factory=list)
    imports_ok: bool = True
    needs_binary: bool = True
    detail: str = ""
    python: str = ""

    @property
    def usable(self) -> bool:
        """Everything the KI declares must work — its binary and its imports.

        A model with a Fortran core that also needs numpy is usable only when
        both are in place, so neither half can be waived.
        """
        if not self.imports_ok:
            return False
        if not self.needs_binary:
            return True                 # a Python-package KI: imports are the model
        return self.present and self.shaped and self.linked and self.responds

    #: The one word the app paints green or red.
    @property
    def state(self) -> str:
        return "ready" if self.usable else "blocked"

    def summary(self) -> str:
        if self.kind == "unknown":
            return f"cannot verify — {self.detail}"
        if not self.imports_ok:
            return f"missing Python modules: {', '.join(self.missing[:6])}"
        if self.usable and not self.needs_binary:
            return "runnable (python package) — all declared imports resolve"
        if self.usable:
            return f"runnable ({self.kind}) — {self.detail}"
        if not self.present:
            return f"not found — {self.detail}"
        if not self.shaped:
            return f"wrong kind of executable — {self.detail}"
        if not self.linked:
            if self.detail:
                return self.detail
            what = "shared libraries" if self.kind in ("elf", "macho", "pe") else "imports"
            return f"missing {what}: {', '.join(self.missing[:6])}"
        return f"does not execute — {self.detail}"

    def as_dict(self) -> dict:
        return {"model": self.model, "binary": self.binary, "state": self.state,
                "present": self.present, "shaped": self.shaped,
                "linked": self.linked, "responds": self.responds,
                "kind": self.kind, "missing": self.missing,
                "detail": self.detail, "python": self.python,
                "summary": self.summary()}


# ---------------------------------------------------------------- locating

def _static_path(node: ast.AST, names: dict[str, str]) -> str | None:
    """Evaluate the small path-expression subset used by generated preflights."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = _static_path(node.left, names), _static_path(node.right, names)
        return str(Path(left) / right) if left is not None and right is not None else None
    if isinstance(node, ast.Attribute):
        value = _static_path(node.value, names)
        if value is not None and node.attr == "parent":
            return str(Path(value).parent)
    if not isinstance(node, ast.Call):
        return None

    args = [_static_path(arg, names) for arg in node.args]
    if isinstance(node.func, ast.Name) and node.func.id in {"Path", "str"}:
        return args[0] if args and args[0] is not None else None
    if isinstance(node.func, ast.Attribute):
        chain = []
        target: ast.AST = node.func
        while isinstance(target, ast.Attribute):
            chain.append(target.attr)
            target = target.value
        if isinstance(target, ast.Name):
            chain.append(target.id)
        dotted = ".".join(reversed(chain))
        if dotted == "os.path.join" and args and all(a is not None for a in args):
            return os.path.join(*args)
        if dotted == "os.path.dirname" and args and args[0] is not None:
            return os.path.dirname(args[0])
        if dotted == "os.path.abspath" and args and args[0] is not None:
            return os.path.abspath(args[0])
        if node.func.attr == "resolve":
            base = _static_path(node.func.value, names)
            return str(Path(base).resolve()) if base is not None else None
    return None


def declared(ki) -> list[str]:
    """Executable paths the KI's preflight names, tokens and all.

    Generated preflights also check data, documentation, and Python
    environments.  Treating the first literal ``check_file`` as the model
    binary made CRHM's elevation NetCDF look executable.  Read only calls whose
    own ``executable`` argument is true, while resolving their simple Path or
    ``os.path`` assignments without executing the preflight.
    """
    pre = getattr(ki, "preflight", None)
    if not pre or not Path(pre).is_file():
        return []
    text = Path(pre).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    names = {"__file__": str(Path(pre))}
    signatures: dict[str, tuple[int, int]] = {}
    for stmt in tree.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = [arg.arg for arg in stmt.args.args]
        if "path" in params and "executable" in params:
            signatures[stmt.name] = (params.index("path"),
                                     params.index("executable"))

    # Resolve module-level constants in source order.  A few generated KIs use
    # Path division; older ones use os.path.dirname/join.
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            value = _static_path(stmt.value, names)
            if value is not None:
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        names[target.id] = value

    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = (node.func.id if isinstance(node.func, ast.Name)
                     else node.func.attr if isinstance(node.func, ast.Attribute)
                     else "")
        signature = signatures.get(func_name)
        if signature is None:
            continue
        path_index, executable_index = signature
        explicit = next((kw.value for kw in node.keywords
                         if kw.arg == "executable"), None)
        if explicit is None and executable_index is not None and len(node.args) > executable_index:
            explicit = node.args[executable_index]
        if not (isinstance(explicit, ast.Constant) and explicit.value is True):
            continue
        if len(node.args) <= path_index:
            continue
        value = _static_path(node.args[path_index], names)
        if value and value not in out:
            out.append(value)
    return out


def declared_dirs(ki) -> list[str]:
    """Directories the KI's preflight requires, from its own ``check_dir`` calls."""
    pre = getattr(ki, "preflight", None)
    if not pre or not Path(pre).is_file():
        return []
    text = Path(pre).read_text(encoding="utf-8", errors="replace")
    return [m.group(1) for m in
            re.finditer(r"""check_dir\(\s*['"]([^'"]+)['"]""", text)]


def declared_imports(ki) -> list[str]:
    """Modules the KI's preflight requires, from its own ``check_import`` calls.

    125 of the 127 KIs declare imports and 56 declare no executable at all: for
    a model shipped as a Python package, importing it *is* running it. Judging
    those on a binary they never claimed to have would paint every one of them
    red while they work perfectly.
    """
    pre = getattr(ki, "preflight", None)
    if not pre or not Path(pre).is_file():
        return []
    text = Path(pre).read_text(encoding="utf-8", errors="replace")
    seen, out = set(), []
    for m in re.finditer(r"""check_import\(\s*['"]([\w.]+)['"]""", text):
        mod = m.group(1)
        if mod not in seen:
            seen.add(mod)
            out.append(mod)
    # Contract preflights are not all generated from the same template.  Some
    # take ``checks`` or ``python_path`` before ``module``; some call the helper
    # ``check_python_import``/``check_import_with_python``.  Read the helper's
    # own signature so labels and interpreter paths are never mistaken for
    # module names.
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    module_indexes: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if "import" not in node.name:
            continue
        params = [arg.arg for arg in node.args.args]
        if "module" in params:
            module_indexes[node.name] = params.index("module")
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = _static_path(node.value, constants)
            if value is not None:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = value
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.id if isinstance(node.func, ast.Name) else
                node.func.attr if isinstance(node.func, ast.Attribute) else "")
        index = module_indexes.get(name)
        if index is None:
            continue
        keyword = next((kw.value for kw in node.keywords if kw.arg == "module"), None)
        value_node = keyword if keyword is not None else (
            node.args[index] if len(node.args) > index else None)
        module = _static_path(value_node, constants) if value_node is not None else None
        if module and re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module):
            if module not in seen:
                seen.add(module)
                out.append(module)
    # Resolve the common ``for module in ('numpy', ...): check_import(...,
    # module)`` form.  Only loops whose body calls a recognised import helper
    # are considered, so unrelated lists of filenames or labels stay out.
    for loop in (n for n in ast.walk(tree) if isinstance(n, ast.For)):
        if not isinstance(loop.target, ast.Name):
            continue
        values = loop.iter.elts if isinstance(loop.iter, (ast.Tuple, ast.List)) else []
        modules = [v.value for v in values
                   if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        if len(modules) != len(values):
            continue
        uses_module = False
        for call in (n for stmt in loop.body for n in ast.walk(stmt)
                     if isinstance(n, ast.Call)):
            name = (call.func.id if isinstance(call.func, ast.Name) else
                    call.func.attr if isinstance(call.func, ast.Attribute) else "")
            index = module_indexes.get(name)
            if index is not None and len(call.args) > index:
                uses_module |= (isinstance(call.args[index], ast.Name) and
                                call.args[index].id == loop.target.id)
        if uses_module:
            for module in modules:
                if (module not in seen and
                        re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module)):
                    seen.add(module)
                    out.append(module)
    return out


def missing_imports(mods: list[str], python: str, cwd: Path | None = None) -> list[str]:
    """Which of these modules this interpreter cannot find. One probe, not N."""
    if not mods:
        return []
    # find_spec imports parent packages, and packages print things: pysteps
    # announces its config file on stdout. Unmarked output would be read back
    # as the name of a missing module, so every answer carries a marker and
    # anything else on the stream is somebody else's noise.
    probe = ("import importlib.util as u\n"
             "for m in %r:\n"
             "    try:\n"
             "        ok = u.find_spec(m) is not None\n"
             "    except Exception:\n"
             "        ok = False\n"
             "    if not ok:\n"
             "        print('%s' + m)" % (mods, _MARK))
    try:
        r = subprocess.run([python, "-c", probe], capture_output=True, text=True,
                           timeout=180, cwd=str(cwd) if cwd else None)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.split(_MARK, 1)[1].strip() for ln in r.stdout.splitlines()
            if _MARK in ln]


def _package_module(man) -> str:
    """The import name promised by a pip manifest, when it promises one."""
    acquire = getattr(man, "acquire", None) if man is not None else None
    if not acquire or getattr(acquire, "strategy", "") != "pip":
        return ""
    raw = getattr(acquire, "produces", None) or getattr(acquire, "package", None) or ""
    # A distribution may be pinned or use extras; imports use underscores.
    raw = re.split(r"[<>=!~\[; ]", str(raw), maxsplit=1)[0].strip()
    return raw.replace("-", "_") if re.fullmatch(r"[A-Za-z0-9_.-]+", raw) else ""


def _python_candidates(cfg, configured: str) -> list[str]:
    """Likely interpreters an install agent may have created in this workspace.

    Agent providers do not share one venv convention.  Accept the small set of
    conventional, project-contained layouts instead of requiring every model
    to rewrite ``kiss.toml`` perfectly before GeoForge can see a successful
    install.  The selected path is returned in the verdict and persisted by
    the setup handler.
    """
    candidates: list[Path | str] = []
    roles = getattr(cfg, "roles", {}) if cfg is not None else {}
    root = Path(getattr(cfg, "root", Path.cwd())) if cfg is not None else Path.cwd()
    binaries = Path(roles.get("binaries", root / "binaries"))
    python_env = Path(roles.get("python_env", root / "venv"))
    for base in (python_env, root / "venv", root / ".venv",
                 binaries / "venv", binaries / ".venv"):
        candidates.extend((base / "bin" / "python", base / "Scripts" / "python.exe"))
    if binaries.is_dir():
        candidates.extend(binaries.glob("*/venv/bin/python"))
        candidates.extend(binaries.glob("*/.venv/bin/python"))
        candidates.extend(binaries.glob("*/venv/Scripts/python.exe"))
        candidates.extend(binaries.glob("*/.venv/Scripts/python.exe"))
    candidates.append(configured)
    out: list[str] = []
    for candidate in candidates:
        value = str(candidate)
        resolved = shutil.which(value) or (value if Path(value).is_file() else "")
        if resolved and resolved not in out:
            out.append(resolved)
    return out


def select_python(cfg, configured: str, modules: list[str], cwd: Path | None = None) -> str:
    """Choose the project-contained interpreter that imports the model."""
    for candidate in _python_candidates(cfg, configured):
        if not modules or not missing_imports(modules, candidate, cwd):
            return candidate
    return configured


def find_binary(ki, man=None, cfg=None, harvested: dict | None = None) -> Path | None:
    """Locate the model executable from what the KI and manifest declare."""
    cands: list[Path] = []
    if man is not None and getattr(man, "acquire", None) and getattr(man.acquire, "produces", None) and cfg is not None:
        cands.append(cfg.roles["binaries"] / (man.install_dir or ki.name) / man.acquire.produces)
    rel = (harvested or {}).get(ki.name)
    if rel and cfg is not None:
        cands.append(cfg.roles["binaries"] / ki.name / rel)
    # Last resort: whatever the KI's own preflight names as its binary.
    for p in declared(ki):
        if p.startswith("KISSPATH_"):
            if cfg is None:
                continue                # unresolvable without an install
            try:
                from .port import unsubstitute
                p = unsubstitute(p, cfg)[0]
            except Exception:
                continue
        cands.append(Path(p))
    # Harvested paths and old KI preflights were produced on Linux/macOS.  The
    # same native build normally lands at ``foo.exe`` on Windows, while a venv
    # uses ``Scripts/python.exe`` rather than ``bin/python``.  Keep the declared
    # candidate as the contract, but probe its native spelling before calling a
    # successful Windows installation missing.
    native: list[Path] = []
    for c in cands:
        variants = [c]
        if os.name == "nt":
            if not c.suffix:
                variants.insert(0, c.with_suffix(".exe"))
            parts = list(c.parts)
            if len(parts) >= 2 and parts[-2:] in (["bin", "python"],
                                                  ["bin", "python3"]):
                variants.insert(0, Path(*parts[:-2], "Scripts", "python.exe"))
        for candidate in variants:
            if candidate not in native:
                native.append(candidate)
    cands = native

    for c in cands:
        if c.is_file():
            return c
    # Agents may correctly build the promised executable under an upstream
    # repository layout that differs from an old harvested relative path.
    # Search only this model's managed binaries tree, and only for the exact
    # promised basename (plus the native .exe spelling).  This accepts
    # Cell2Fire/Cell2Fire/Cell2Fire.exe without mistaking compiler probes or a
    # coupled model for the requested runtime.
    if cfg is not None and cands:
        roles = getattr(cfg, "roles", {}) or {}
        binaries = Path(roles.get("binaries", Path(cfg.root) / "binaries"))
        roots = [binaries / ki.name]
        install_dir = getattr(man, "install_dir", "") if man is not None else ""
        if install_dir:
            roots.insert(0, binaries / install_dir)
        lang = str((getattr(ki, "meta", None) or {}).get("language") or "").lower()
        if lang in COMPILED:
            # A Windows path-length workaround may force the agent to use a
            # shallow sibling (CRHM installs at binaries/crhm/bin/crhm.exe).
            # The binaries role is still an isolated software-only boundary.
            roots.append(binaries)
        wanted = {c.name.lower() for c in cands}
        if os.name == "nt":
            wanted |= {name + ".exe" for name in wanted
                       if not Path(name).suffix}
        matches: list[Path] = []
        for root in roots:
            if not root.is_dir():
                continue
            try:
                matches.extend(p for p in root.rglob("*")
                               if p.is_file() and p.name.lower() in wanted)
            except OSError:
                continue
        if matches:
            return min(set(matches), key=lambda p: (len(p.parts), len(str(p))))
    return cands[0] if cands else None


# ---------------------------------------------------------------- shape

def _file_kind(p: Path) -> str:
    """What sort of executable this is. Magic bytes first, suffix second.

    Suffix is not a fallback for style: plenty of working models are Python
    files with no shebang, and calling those "unknown" would paint a working
    install red.
    """
    try:
        head = p.open("rb").read(4)
    except OSError:
        return "unreadable"
    if head[:4] == b"\x7fELF":
        return "elf"
    if head[:2] == b"MZ":
        return "pe"                     # Windows binary — needs wine here
    if head[:4] in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xce\xfa\xed\xfe"):
        return "macho"
    if head[:2] == b"#!":
        return "script"
    if p.suffix in INTERPRETERS:
        return "script"
    return "other"


def _interpreter(p: Path, python: str | None = None) -> list[str] | None:
    """How to launch a script: its shebang if it has one, else its suffix."""
    try:
        first = p.open("rb").read(256).split(b"\n", 1)[0].decode("utf-8", "replace")
    except OSError:
        first = ""
    if first.startswith("#!"):
        parts = first[2:].strip().split()
        if parts:
            if parts[0].endswith("env") and len(parts) > 1:
                parts = parts[1:]
            exe = shutil.which(parts[0]) or (parts[0] if Path(parts[0]).exists() else None)
            if exe and not (python and "python" in Path(exe).name):
                return [exe] + parts[1:]
    argv = INTERPRETERS.get(p.suffix)
    if argv is None:
        return None
    argv = list(argv)
    if p.suffix == ".py" and python:
        argv[0] = python                # the KI's own venv, not ours
    resolved = shutil.which(argv[0]) or (argv[0] if Path(argv[0]).is_file() else None)
    return [resolved] + argv[1:] if resolved else None


# ---------------------------------------------------------------- linkage

def _missing_libs(p: Path) -> list[str]:
    """Shared libraries the loader cannot resolve. Linux only; [] elsewhere."""
    if platform.system() != "Linux" or not shutil.which("ldd"):
        return []
    try:
        r = subprocess.run(["ldd", str(p)], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.split("=>")[0].strip() for ln in r.stdout.splitlines() if "not found" in ln]


def _missing_imports(p: Path, python: str) -> list[str]:
    """Top-level imports a script needs that this interpreter cannot find.

    The script's own directory goes on the path first: models routinely import
    sibling modules, and reporting those missing would be an artefact of where
    we ran from rather than anything about the install.
    """
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    mods = sorted({(m.group(1) or m.group(2)).split(".")[0]
                   for m in _IMPORT_RE.finditer(src)} - _STDLIB)
    if not mods:
        return []
    probe = ("import sys,importlib.util as u;sys.path.insert(0,%r);"
             "print('\\n'.join(m for m in %r if u.find_spec(m) is None))"
             % (str(p.parent), mods))
    try:
        r = subprocess.run([python, "-c", probe], capture_output=True,
                           text=True, timeout=90, cwd=str(p.parent))
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


# ---------------------------------------------------------------- execution

def _ran(rc: int) -> bool:
    """Did the process actually execute?

    A non-negative code means the program ran and chose it — including codes
    above 127, which several models use (APSIM exits 131, CAM-chem 233).
    Python reports a signal death as a *negative* code; that still proves the
    binary loaded and executed instructions, which is the question here.
    """
    return rc is not None


def check(ki, man=None, cfg=None, harvested: dict | None = None,
          timeout: int = 25, python: str | None = None) -> Verdict:
    """Run the four tests and return a verdict the agent can act on."""
    v = Verdict(model=getattr(ki, "name", str(ki)))
    py = python or (getattr(cfg, "python", None) if cfg else None)
    if not py or getattr(sys, "frozen", False):
        from .install import runtime_python
        py = runtime_python(py)

    # Imports first: they are cheap, they are what 56 of the 127 KIs are made
    # of, and a missing module explains a binary failure more often than the
    # other way round.
    mods = declared_imports(ki)
    package_module = _package_module(man)
    if package_module and package_module not in mods:
        mods.append(package_module)
    py = select_python(cfg, py, mods, getattr(ki, "root", None))
    v.python = py
    if mods:
        v.missing = missing_imports(mods, py, getattr(ki, "root", None))
        v.imports_ok = not v.missing

    lang = str((getattr(ki, "meta", None) or {}).get("language") or "").lower()
    b = find_binary(ki, man, cfg, harvested)
    # A pip-delivered Python model is the imported package. ``produces`` in
    # older manifests often names that module, not a filesystem executable;
    # turning it into <binaries>/<model>/<module> caused a false red after a
    # completely successful install (COSIPY is the real case).
    python_package = bool(package_module) and lang == "python"
    v.needs_binary = (not python_package and
                      (b is not None or bool(declared(ki)) or lang in COMPILED))

    if not v.needs_binary and not mods:
        # SUMMA's preflight declares no file and no import. Passing it because
        # nothing failed would be a vacuous green: the check that examines
        # nothing always succeeds. Absence of a test is not evidence of health.
        v.kind = "unknown"
        v.imports_ok = False
        v.detail = ("the KI declares nothing to run — no executable and no "
                    "imports to check, so its state cannot be established")
        v.missing = []
        return v

    if not v.needs_binary:
        # Nothing executable is claimed; the imports were the whole contract.
        v.kind = "python package"
        v.detail = (f"{len(mods)} declared imports resolve" if v.imports_ok
                    else f"missing: {', '.join(v.missing[:4])}")
        return v

    if b is None and lang in COMPILED and not declared(ki):
        v.kind = "unknown"
        v.imports_ok = False
        v.detail = (f"a {lang} model must have a binary, but the KI declares "
                    f"none — nothing to verify")
        return v
    if not v.imports_ok:
        v.kind = v.kind or "python package"
        v.detail = f"missing: {', '.join(v.missing[:4])}"
        return v
    if b is None:
        # "Declares nothing" and "declares something we cannot resolve here"
        # are different problems with different fixes; saying the first when
        # the second is true sends the user looking for a defect in the KI.
        d = declared(ki)
        v.detail = (f"declared at {d[0]} — no install on this machine "
                    f"(run: kiss init {v.model})") if d else "the KI declares no executable"
        return v
    v.binary = str(b)
    if not b.is_file():
        # Several Python KIs point check_file at a package directory rather
        # than an executable — WOFOST names .../pcse, which is not a file
        # anywhere and imports perfectly from site-packages. The declaration is
        # about the package, so answer the question the package can answer.
        if lang == "python" and not missing_imports([b.name], py):
            v.present = v.shaped = v.linked = v.responds = True
            v.kind = "python package"
            v.detail = f"{b.name} imports (installed as a package, not a file)"
            return v
        v.detail = f"nothing at {b}"
        return v
    v.present = True
    v.kind = _file_kind(b)

    argv0: list[str]
    native = {"Linux": "elf", "Darwin": "macho", "Windows": "pe"}.get(platform.system(), "elf")
    if v.kind == "script":
        interp = _interpreter(b, py)
        if interp is None:
            v.detail = f"no interpreter for {b.suffix or 'this script'} on this machine"
            return v
        v.shaped, argv0 = True, interp + [str(b)]
    elif v.kind == "pe" and platform.system() != "Windows":
        if not shutil.which("wine"):
            v.detail = "Windows binary and wine is not installed"
            return v
        v.shaped, argv0 = True, ["wine", str(b)]
    elif v.kind in ("elf", "macho", "pe"):
        if v.kind != native:
            v.detail = f"{v.kind} binary on {platform.system()} — built for another platform"
            return v
        if not os.access(b, os.X_OK):
            v.detail = f"not executable — chmod +x {b}"
            return v
        v.shaped, argv0 = True, [str(b)]
    else:
        v.detail = f"not an executable ({v.kind})"
        return v

    # For a compiled binary ldd is authoritative: if the loader cannot resolve a
    # library, the program will not start, full stop. For a script it is only a
    # hint — models routinely extend sys.path at import time (AquaCrop pulls
    # compute_eto_penman_monteith from tools/s3_weather_prep/), so a static scan
    # reports absences that do not exist at run time. There, running it is the
    # ground truth and the scan is kept back to explain a failure.
    scan: list[str] = []
    if v.kind in ("elf", "macho"):
        v.missing = _missing_libs(b)
        v.linked = not v.missing
        if not v.linked:
            return v
    else:
        v.linked = True
        if b.suffix == ".py":
            scan = _missing_imports(b, py)

    rc = None
    for flag in PROBE_FLAGS:
        argv = argv0 + ([flag] if flag else [])
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                               errors="replace", cwd=str(b.parent), stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            # A model that starts solving instead of printing help is running.
            v.responds = True
            v.detail = f"ran — still working after {timeout}s ({flag or 'no arguments'})"
            return v
        except OSError as e:
            v.detail = f"could not execute: {e}"
            return v
        rc, out = r.returncode, (r.stdout + r.stderr).strip()
        gap = _runtime_gap(out) if rc != 0 else ""
        if gap:
            v.linked = False
            v.missing = scan or [gap]
            v.detail = f"{gap} — {out.splitlines()[0].strip()[:120]}" if out else gap
            return v
        if _ran(rc):
            v.responds = True
            if rc < 0:
                v.detail = f"ran and crashed on probe (signal {-rc}) — loads and executes"
            else:
                v.detail = (out.splitlines() or [f"exit {rc}, no output"])[0].strip()[:160]
            return v
    v.detail = f"exit {rc}"
    return v


def check_all(kis, **kw) -> list[Verdict]:
    return [check(ki, **kw) for ki in kis]


# ---------------------------------------------------------------- caching

def cache_path(workroot: Path, ki_name: str) -> Path:
    return Path(workroot) / ki_name.lower() / "runnable.json"


def load(workroot: Path, ki_name: str, max_age: float = 86400.0) -> dict | None:
    """A recent verdict, or None. Probing 127 models takes minutes; a page
    load must not do it. Verdicts go stale when the machine changes, so they
    expire rather than persisting as a claim about a machine that has moved on.
    """
    import json
    import time
    p = cache_path(workroot, ki_name)
    try:
        if time.time() - p.stat().st_mtime > max_age:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(workroot: Path, v: Verdict) -> None:
    import json
    import time
    p = cache_path(workroot, v.model)
    p.parent.mkdir(parents=True, exist_ok=True)
    d = v.as_dict()
    d["checked_at"] = time.time()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2), encoding="utf-8")
    tmp.replace(p)
