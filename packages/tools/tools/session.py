"""User directories, Makevars paths, Ghostscript, and the standard package names."""

from __future__ import annotations

import os
import shutil
from typing import Any


def match_arg(value: str, choices: list[str]) -> str:
    """Unique prefix match, the same rule as match.arg."""
    if value in choices:
        return value
    hits = [choice for choice in choices if choice.startswith(value)]
    shown = ", ".join(f'"{choice}"' for choice in choices)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError(f"'{value}' should be one of {shown}")
    raise ValueError(f"'{value}' matches more than one of {shown}")


def _home() -> str:
    return os.path.realpath(os.path.expanduser("~"))


def R_user_dir(package: str, which: str = "data") -> str:
    """The per-user data, config, or cache directory for one package."""
    if not isinstance(package, str):
        raise ValueError("package must be a character string")
    which = match_arg(which, ["data", "config", "cache"])
    home = _home()
    if which == "data":
        path = os.environ.get("R_USER_DATA_DIR") or os.environ.get("XDG_DATA_HOME")
        if not path:
            path = os.path.join(home, ".local", "share")
    elif which == "config":
        path = os.environ.get("R_USER_CONFIG_DIR") or os.environ.get("XDG_CONFIG_HOME")
        if not path:
            path = os.path.join(home, ".config")
    else:
        path = os.environ.get("R_USER_CACHE_DIR") or os.environ.get("XDG_CACHE_HOME")
        if not path:
            path = os.path.join(home, ".cache")
    return os.path.join(path, "R", package)


def makevars_user() -> str:
    """The user Makevars file, or an empty string when R would return character(0)."""
    if os.name == "nt":
        if "R_MAKEVARS_USER" in os.environ:
            path = os.environ["R_MAKEVARS_USER"]
            return path if os.path.exists(path) else ""
        if os.environ.get("R_ARCH") == "/x64":
            for name in ("Makevars.ucrt", "Makevars.win64"):
                path = os.path.expanduser(f"~/.R/{name}")
                if os.path.exists(path):
                    return path
        for name in ("Makevars.win", "Makevars"):
            path = os.path.expanduser(f"~/.R/{name}")
            if os.path.exists(path):
                return path
        return ""
    if "R_MAKEVARS_USER" in os.environ:
        path = os.environ["R_MAKEVARS_USER"]
        return path if os.path.exists(path) else ""
    platform = os.environ.get("R_PLATFORM", "")
    if platform:
        path = os.path.expanduser(f"~/.R/Makevars-{platform}")
        if os.path.exists(path):
            return path
    path = os.path.expanduser("~/.R/Makevars")
    if os.path.exists(path):
        return path
    return ""


def makevars_site() -> str:
    """The site Makevars file, or an empty string when none exists."""
    if "R_MAKEVARS_SITE" in os.environ:
        path = os.environ["R_MAKEVARS_SITE"]
    else:
        etc = os.environ.get("R_HOME", "")
        # R uses R.home("etc"), which is <R_HOME>/etc plus R_ARCH.
        if not etc:
            etc = _r_home_etc()
        else:
            etc = os.path.join(etc, "etc" + os.environ.get("R_ARCH", ""))
        path = os.path.join(etc, "Makevars.site")
    return path if os.path.exists(path) else ""


def _r_home_etc() -> str:
    home = os.environ.get("R_HOME", "")
    if home:
        return os.path.join(home, "etc" + os.environ.get("R_ARCH", ""))
    return os.path.join("/usr/lib/R", "etc" + os.environ.get("R_ARCH", ""))


def find_gs_cmd(gs_cmd: str = "") -> str:
    """The Ghostscript executable, or an empty string when it is not on PATH."""
    if not gs_cmd:
        if os.name == "nt":
            command = os.environ.get("R_GSCMD") or os.environ.get("GSC") or ""
            found = shutil.which(command) if command else None
            if not found:
                found = shutil.which("gswin64c") or shutil.which("gswin32c")
            return found or ""
        return shutil.which(os.environ.get("R_GSCMD", "gs")) or ""
    return shutil.which(gs_cmd) or ""


def standard_package_names() -> dict[str, list[str]]:
    """Names of the base and recommended packages shipped with R."""
    return {
        "base": [
            "base", "tools", "utils", "grDevices", "graphics", "stats", "datasets",
            "methods", "grid", "splines", "stats4", "tcltk", "compiler", "parallel",
        ],
        "recommended": [
            "MASS", "lattice", "Matrix", "nlme", "survival", "boot", "cluster",
            "codetools", "foreign", "KernSmooth", "rpart", "class", "nnet",
            "spatial", "mgcv",
        ],
    }


LANG_ELTS = (
    "(", "{", ":", "~", "<-", "<<-", "=", "[", "[[", "[[<-", "[<-",
    "@", "@<-", "$", "$<-", "&&", "||", "break", "for", "function",
    "if", "next", "repeat", "return", "while",
)


def lang_elts() -> tuple[str, ...]:
    """The operators and control-flow names R treats as language elements."""
    return LANG_ELTS
