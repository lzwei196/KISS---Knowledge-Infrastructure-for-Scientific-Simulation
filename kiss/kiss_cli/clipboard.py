"""Small native clipboard bridge for the desktop webview.

WKWebView normally handles Cmd+C/V itself, but pywebview intentionally removes
its right-click menu and some macOS versions fail to route the keyboard action
to an HTML textarea.  The UI therefore has a same-origin fallback endpoint.
On macOS the frozen app already bundles PyObjC for WKWebView, so the bridge uses
``NSPasteboard`` directly.  This matters when a GUI launch has a restricted or
minimal shell environment: ``pbcopy``/``pbpaste`` may fail even though the
native pasteboard is available.  The commands remain a fallback for source
installs that do not include PyObjC.

Windows goes through PowerShell's ``Get-Clipboard``/``Set-Clipboard``, which are
built in from PowerShell 5 (Windows 10) onward, so there is nothing to install
and no pywin32 to bundle.  Until this existed Windows fell through to the "no
clipboard here" branch and the bridge silently returned nothing — copy did
nothing and paste pasted nothing, with no error to explain it.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess

MAX_CHARS = 2_000_000

# A windowed build owns no console, so Windows hands every child a fresh one and
# a black window flashes over the app — the same defect CREATE_NO_WINDOW fixes
# for the agent CLIs in providers.py. A clipboard round-trip happens on every
# copy and paste, so it would flash constantly.
_SPAWN: dict = ({"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
                if os.name == "nt" else {})


def _powershell(script: str) -> list[str]:
    """Argv for one self-contained PowerShell command.

    -NoProfile because a user profile can print banners into stdout, and this
    parses stdout as clipboard content.
    """
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


# Both directions pin UTF-8 at the PowerShell boundary as well as at the Python
# one. Left alone, the console uses the locale codepage — cp936 on a Chinese
# install — and text round-trips as mojibake, which is exactly how prompts and
# replies were being corrupted before the CLI spawns were pinned the same way.
# Console I/O rather than Write-Output: PowerShell appends a newline to piped
# output, and a clipboard bridge must not invent one.
_PS_READ = (
    "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
    "$t = Get-Clipboard -Raw; "
    "if ($null -ne $t) { [Console]::Out.Write($t) }"
)
_PS_WRITE = (
    "[Console]::InputEncoding=[Text.Encoding]::UTF8; "
    "$t = [Console]::In.ReadToEnd(); "
    "Set-Clipboard -Value $t"
)


def _mac_read() -> str | None:
    try:
        import AppKit
        value = AppKit.NSPasteboard.generalPasteboard().stringForType_(
            AppKit.NSPasteboardTypeString)
        return str(value or "")[:MAX_CHARS]
    except (ImportError, AttributeError, OSError):
        return None


def _mac_write(text: str) -> bool | None:
    try:
        import AppKit
        board = AppKit.NSPasteboard.generalPasteboard()
        board.clearContents()
        return bool(board.setString_forType_(text, AppKit.NSPasteboardTypeString))
    except (ImportError, AttributeError, OSError):
        return None


def read_text() -> str:
    system = platform.system()
    if system == "Darwin":
        native = _mac_read()
        if native is not None:
            return native
        cmd = ["/usr/bin/pbpaste"]
    elif system == "Windows":
        cmd = _powershell(_PS_READ)
    elif system == "Linux" and shutil.which("wl-paste"):
        cmd = ["wl-paste", "--no-newline"]
    elif system == "Linux" and shutil.which("xclip"):
        cmd = ["xclip", "-selection", "clipboard", "-o"]
    else:
        return ""
    try:
        result = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", errors="replace",
            timeout=5, **_SPAWN,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "")[:MAX_CHARS] if result.returncode == 0 else ""


def write_text(text: str) -> bool:
    text = str(text)[:MAX_CHARS]
    system = platform.system()
    if system == "Darwin":
        native = _mac_write(text)
        if native is not None:
            return native
        cmd = ["/usr/bin/pbcopy"]
    elif system == "Windows":
        cmd = _powershell(_PS_WRITE)
    elif system == "Linux" and shutil.which("wl-copy"):
        cmd = ["wl-copy"]
    elif system == "Linux" and shutil.which("xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    else:
        return False
    try:
        result = subprocess.run(
            cmd, input=text, capture_output=True, encoding="utf-8",
            errors="replace", timeout=5, **_SPAWN,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
