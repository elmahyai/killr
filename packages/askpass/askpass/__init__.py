"""Password prompts.

A non-interactive session returns None. An interactive terminal prompt uses
getpass so the password is not echoed.
"""

import getpass
import os
import sys

options = {}


def is_interactive():
    opt = options.get("rlib_interactive", None)
    if opt is True:
        return True
    if opt is False:
        return False
    if str(options.get("knitr.in.progress", "false")).lower() == "true":
        return False
    if os.environ.get("TESTTHAT") == "true":
        return False
    # R's interactive() is false under Rscript even when stdin is a terminal.
    return hasattr(sys, "ps1")


def ask_password_default(prompt):
    if not is_interactive():
        return None
    if os.name == "nt":
        return _ask_helper(prompt)
    if sys.platform == "darwin" and not sys.stdin.isatty():
        return _ask_helper(prompt)
    return readline_silent(prompt)


def readline_silent(prompt, icon="\U0001f511 "):
    """Read one line without echoing it."""
    print(prompt, flush=True)
    out = getpass.getpass(icon)
    print(" OK", flush=True)
    return out


def _ask_helper(prompt):
    from r_sys import exec_internal

    try:
        result = exec_internal(ssh_askpass(), [prompt], timeout=120)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return None
    text = bytes(result["stdout"]).decode("utf-8", "replace")
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\n") or text.endswith("\r"):
        return text[:-1]
    return text


def askpass(prompt="Please enter your password: "):
    """Ask for a password. Non-interactive sessions return None."""
    function = options.get("askpass", ask_password_default)
    return function(prompt)


def ssh_askpass():
    """Path of the bundled askpass helper.

    Linux has no helper, so this is None, matching R.
    """
    if os.name == "nt" or sys.platform == "darwin":
        name = "mac-askpass" if sys.platform == "darwin" else "win-askpass.exe"
        here = os.path.join(os.path.dirname(__file__), name)
        if os.path.exists(here):
            return here
        raise FileNotFoundError(name)
    return None
