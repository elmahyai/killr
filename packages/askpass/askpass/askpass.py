"""Password prompts and the SSH_ASKPASS program path."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import termios
from pathlib import Path

from askpass._options import get_option

_ICON = "\U0001f511 "
_HERE = Path(__file__).resolve().parent


def askpass(prompt: str = "Please enter your password: "):
    """Prompt for a password, or call the function stored as the askpass option.

    A non-interactive session returns None. That includes Rscript, knitr, and
    TESTTHAT=true. Set the rlib_interactive option to True to force a prompt.
    """
    function = get_option("askpass", _ask_password_default)
    return function(prompt)


def ssh_askpass():
    """Path of the dialog program used as SSH_ASKPASS and GIT_ASKPASS.

    Linux has no bundled dialog, so this is None. macOS returns mac-askpass.
    """
    return _askpass_path(simple=False)


def _ask_password_default(prompt: str):
    if not _is_interactive():
        return None
    if _is_windows():
        return _askpass_windows(prompt)
    if _is_macos() and not _stdin_isatty():
        return _askpass_mac(prompt)
    return _readline_silent(prompt)


def _is_interactive() -> bool:
    option = get_option("rlib_interactive")
    if option is True:
        return True
    if option is False:
        return False
    if str(get_option("knitr.in.progress", "false")).lower() == "true":
        return False
    if os.environ.get("TESTTHAT") == "true":
        return False
    # R's interactive() is false under Rscript even when stdin is a terminal.
    return hasattr(sys, "ps1") or sys.flags.interactive


def _is_windows() -> bool:
    return os.name == "nt"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _stdin_isatty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _askpass_path(simple: bool = True):
    if _is_windows():
        suffix = "32" if _pointer_bytes() == 4 else ""
        return _bundled(f"win-askpass{suffix}.exe")
    if _is_macos():
        name = "mac-simplepass" if simple is True else "mac-askpass"
        return _bundled(name)
    return None


def _pointer_bytes() -> int:
    return 8 if sys.maxsize > 2**32 else 4


def _bundled(name: str) -> str:
    path = _HERE / name
    if not path.is_file():
        raise FileNotFoundError("No file found")
    return str(path)


def _askpass_windows(prompt: str, user: str | None = None):
    try:
        args = [prompt] if user is None else [prompt, user]
        stdout = _exec_internal(_askpass_path(), args, timeout=120)
        return _out_without_eol(stdout)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return None


def _askpass_mac(prompt: str):
    try:
        stdout = _exec_internal(_askpass_path(), [prompt], timeout=120)
        return _out_without_eol(stdout)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return None


def _exec_internal(command: str | None, args: list[str], timeout: float):
    """Run a dialog the way sys::exec_internal does, and return its stdout."""
    if not command:
        raise FileNotFoundError("No file found")
    completed = subprocess.run(
        [command, *args],
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"System command {command!r} failed with status {completed.returncode}"
        )
    return completed.stdout


def _out_without_eol(raw: bytes) -> str:
    if b"\x00" in raw:
        raise ValueError("embedded nul in string")
    text = raw.decode()
    return re.sub(r"\r?\n$", "", text)


def _readline_silent(prompt: str, icon: str = _ICON) -> str:
    restore = None
    if os.name != "nt" and _stdin_isatty():
        restore = _echo_off()
    try:
        sys.stdout.write(f"{prompt} \n")
        sys.stdout.flush()
        entered = input(icon)
        sys.stdout.write(" OK\n")
        sys.stdout.flush()
        return entered
    finally:
        if restore is not None:
            _echo_restore(restore)


def _echo_off():
    """Clear the terminal echo flag. None means stty -echo did not succeed."""
    try:
        descriptor = sys.stdin.fileno()
        previous = termios.tcgetattr(descriptor)
        updated = termios.tcgetattr(descriptor)
        updated[3] = updated[3] & ~termios.ECHO
        termios.tcsetattr(descriptor, termios.TCSANOW, updated)
    except Exception:
        return None
    return descriptor, previous


def _echo_restore(saved) -> None:
    descriptor, previous = saved
    try:
        termios.tcsetattr(descriptor, termios.TCSANOW, previous)
    except Exception:
        return


def _var_exists(name: str) -> bool:
    return len(os.environ.get(name, "")) > 0


def _cmd_exists(command: str) -> bool:
    return len(command) > 0 and shutil.which(command) is not None


def _normalize(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/")


def _fix_rstudio_path() -> None:
    rs_path = os.environ.get("RS_RPOSTBACK_PATH", "")
    git_askpass = os.environ.get("GIT_ASKPASS", "")
    if not rs_path or _cmd_exists(git_askpass):
        return
    current = os.environ.get("PATH", "")
    normalized = _normalize(rs_path)
    if normalized in current:
        return
    extra = []
    for item in (rs_path, rs_path.replace("rpostback", "postback")):
        path = _normalize(item)
        if path not in extra:
            extra.append(path)
    parts = [current, *extra] if current else extra
    os.environ["PATH"] = os.pathsep.join(parts)


def _setup_askpass_vars() -> None:
    if _var_exists("RSTUDIO"):
        _fix_rstudio_path()
        return
    if _is_windows() or (_is_macos() and not _stdin_isatty()):
        program = ssh_askpass()
        if program and not _var_exists("GIT_ASKPASS"):
            os.environ["GIT_ASKPASS"] = program
        if program and not _var_exists("SSH_ASKPASS"):
            os.environ["SSH_ASKPASS"] = program


_setup_askpass_vars()
