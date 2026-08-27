"""Tiny dependency-free Windows notification-area presence indicator."""

from __future__ import annotations

import ctypes
import threading
import webbrowser
from ctypes import wintypes


WM_DESTROY = 0x0002
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_APP = 0x8000
TRAY_MESSAGE = WM_APP + 17
NIM_ADD = 0
NIF_MESSAGE = 0x01
NIF_ICON = 0x02
NIF_TIP = 0x04
IDI_APPLICATION = 32512


class _NotifyIconData(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


def start(url: str) -> threading.Thread | None:
    """Show a tray icon whose double-click reopens *url*. Never blocks startup."""
    if not hasattr(ctypes, "windll"):
        return None

    def run() -> None:
        user32, shell32, kernel32 = (
            ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.kernel32)
        user32.DefWindowProcW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        user32.LoadIconW.restype = wintypes.HICON
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        wndproc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM)

        @wndproc_type
        def wndproc(hwnd, message, wparam, lparam):
            if message == TRAY_MESSAGE and lparam in (WM_LBUTTONDBLCLK, WM_RBUTTONUP):
                webbrowser.open(url)
                return 0
            if message == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        class WndClass(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT), ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
            ]

        instance = kernel32.GetModuleHandleW(None)
        class_name = f"GeoForgeTray-{kernel32.GetCurrentProcessId()}"
        wc = WndClass(0, wndproc, 0, 0, instance, None, None, None, None, class_name)
        if not user32.RegisterClassW(ctypes.byref(wc)):
            return
        hwnd = user32.CreateWindowExW(
            0, class_name, "GeoForge Desktop", 0, 0, 0, 0, 0,
            None, None, instance, None)
        if not hwnd:
            return
        # PyInstaller stores the application icon as resource 1. Fall back to
        # Windows' application icon if that resource is unavailable.
        icon = user32.LoadIconW(instance, ctypes.c_void_p(1))
        if not icon:
            icon = user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))
        data = _NotifyIconData()
        data.cbSize = ctypes.sizeof(data)
        data.hWnd, data.uID = hwnd, 1
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        data.uCallbackMessage, data.hIcon = TRAY_MESSAGE, icon
        data.szTip = "GeoForge Desktop — double-click to open"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data))
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    thread = threading.Thread(target=run, name="geoforge-tray", daemon=True)
    thread.start()
    return thread
