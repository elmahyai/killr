"""System clipboard access used by the clipr translation.

Linux follows clipr: xclip, then xsel, then wl-clipboard. Reading splits on
newlines the way R's scan(sep = "\\n", blank.lines.skip = FALSE) does.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Any

NO_CLIPBOARD = (
    "Clipboard on X11 requires 'xclip' (recommended) or 'xsel'; "
    "Clipboard on Wayland requires 'wl-copy' and 'wl-paste'."
)
NO_DISPLAY = "Clipboard on X11 requires that the DISPLAY envvar be configured."
INTERACTIVE_MESSAGE = (
    "To run write_clip() in non-interactive mode, either call write_clip() "
    "with allow_non_interactive = TRUE, or set the environment variable CLIPR_ALLOW=TRUE"
)
CLIPR_ALLOW_BLOCK = "CLIPR_ALLOW has not been set, so clipr will not run interactively"
AVAILABLE_MESSAGE = "clipr has read/write access to the system clipboard!"
EMPTY_MESSAGE = "System clipboard contained no readable text. Returning NULL."


def sys_type() -> str:
    return platform.system()


def is_interactive() -> bool:
    return bool(getattr(sys, "ps1", None)) and sys.stdin is not None and sys.stdin.isatty()


def permitted(allow: Any) -> bool:
    if allow is None:
        if "CLIPR_ALLOW" in os.environ:
            allow = os.environ["CLIPR_ALLOW"]
        else:
            allow = is_interactive()
    return allow is True or allow == "TRUE"


def require_access(allow: Any) -> None:
    if not permitted(allow):
        raise RuntimeError(INTERACTIVE_MESSAGE)


def as_logical(value: str) -> bool:
    return value.strip().lower() in {"true", "t", "1"}


def message(text: str) -> None:
    print(text, file=sys.stderr)


def scan_lines(data: bytes) -> list[str]:
    if data == b"":
        return []
    return data.decode("utf-8").split("\n")


def read_clipboard() -> list[str]:
    kind = sys_type()
    if kind == "Darwin":
        data = _run_read(["pbpaste"])
    elif kind == "Windows":
        data = _windows_read()
    else:
        data = _linux_read()
    return scan_lines(data)


def write_clipboard(payload: bytes) -> None:
    kind = sys_type()
    if kind == "Darwin":
        _run_write(["pbcopy"], payload)
    elif kind == "Windows":
        _windows_write(payload.decode("utf-8"))
    else:
        _linux_write(payload)


def _linux_read() -> bytes:
    if _has_util(["xclip", "-o", "-selection", "clipboard"]):
        return _capture(["xclip", "-o", "-selection", "clipboard"])
    if _has_util(["xsel", "--clipboard", "--output"]):
        return _capture(["xsel", "--clipboard", "--output"])
    if _has_util(["wl-paste", "--primary"]):
        return _capture(["wl-paste"])
    raise RuntimeError(NO_CLIPBOARD)


def _linux_write(payload: bytes) -> None:
    if _has_util(["xclip", "-o", "-selection", "clipboard"]):
        command = "xclip -i -sel p -f | xclip -i -sel c"
        _shell_write(command, payload)
        return
    if _has_util(["xsel", "--clipboard", "--output"]):
        _shell_write("xsel --clipboard --input", payload)
        return
    if _has_util(["wl-copy", "--help"]):
        _shell_write("wl-copy", payload)
        return
    raise RuntimeError(NO_CLIPBOARD)


def _has_util(argv: list[str]) -> bool:
    if shutil.which(argv[0]) is None:
        return False
    try:
        result = subprocess.run(argv, capture_output=True, check=False)
    except OSError:
        raise RuntimeError(NO_DISPLAY) from None
    if result.returncode != 0:
        raise RuntimeError(NO_DISPLAY)
    return True


def _capture(argv: list[str]) -> bytes:
    try:
        result = subprocess.run(argv, capture_output=True, check=False)
    except OSError:
        raise RuntimeError(NO_DISPLAY) from None
    if result.returncode != 0:
        raise RuntimeError(NO_DISPLAY)
    return result.stdout


def _run_read(argv: list[str]) -> bytes:
    return _capture(argv)


def _run_write(argv: list[str], payload: bytes) -> None:
    try:
        result = subprocess.run(argv, input=payload, capture_output=True, check=False)
    except OSError:
        raise RuntimeError(NO_DISPLAY) from None
    if result.returncode != 0:
        raise RuntimeError(NO_DISPLAY)


def _shell_write(command: str, payload: bytes) -> None:
    # stdout is discarded. xclip -f daemonizes and would otherwise keep a
    # captured stdout pipe open, so the writer would never see EOF.
    try:
        result = subprocess.run(
            command,
            shell=True,
            input=payload,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        raise RuntimeError(NO_DISPLAY) from None
    if result.returncode != 0:
        raise RuntimeError(NO_DISPLAY)


def _windows_read() -> bytes:
    text = _windows_clipboard()
    return text.encode("utf-8")


def _windows_write(text: str) -> None:
    _windows_clipboard(text)


def _windows_clipboard(text: str | None = None) -> str:
    import ctypes
    from ctypes import wintypes

    unicode_format = 13
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    if not user32.OpenClipboard(None):
        raise RuntimeError(NO_CLIPBOARD)
    try:
        if text is None:
            user32.GetClipboardData.argtypes = [wintypes.UINT]
            user32.GetClipboardData.restype = wintypes.HANDLE
            handle = user32.GetClipboardData(unicode_format)
            if not handle:
                return ""
            kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return ""
            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel32.GlobalUnlock(handle)
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard()
        encoded = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(encoded)
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HANDLE
        handle = kernel32.GlobalAlloc(0x0002, size)
        pointer = kernel32.GlobalLock(handle)
        ctypes.memmove(pointer, encoded, size)
        kernel32.GlobalUnlock(handle)
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.SetClipboardData(unicode_format, handle)
        return text
    finally:
        user32.CloseClipboard()
