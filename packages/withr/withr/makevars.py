"""makevars_user, set_makevars, with_makevars, local_makevars (R's makevars.R).

These edit and point R's Makevars file. R reads that file when it builds
packages; Python does not build R packages, so only the file contents and the
R_MAKEVARS_USER variable are translated.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile

from ._scope import current, force
from .envvar import local_envvar, with_envvar
from .tempfiles import _tmp_name

_ASSIGNMENTS = ("=", ":=", "?=", "+=")


def makevars_user() -> list[str]:
    """tools::makevars_user(): the Makevars file in use, as a list of zero or one."""
    user = os.environ.get("R_MAKEVARS_USER")
    if user is not None:
        return [user] if os.path.exists(user) else []
    platform = os.environ.get("R_PLATFORM", "")
    for candidate in (
        os.path.expanduser(f"~/.R/Makevars-{platform}"),
        os.path.expanduser("~/.R/Makevars"),
    ):
        if os.path.exists(candidate):
            return [candidate]
    return []


def set_makevars(variables, old_path=None, new_path=None, assignment: str = "="):
    """Add or replace variables in a Makevars file and write it to ``new_path``.

    Returns the old lines (None when there was no old file). Nothing is written
    when the variables already hold the requested values.
    """
    if not variables:
        return None
    if assignment not in _ASSIGNMENTS:
        raise ValueError(f"`assignment` must be one of {_ASSIGNMENTS}")
    if old_path is None:
        old_path = makevars_user()
    if new_path is None:
        new_path = _tmp_name()
    if isinstance(old_path, str):
        old_path = [old_path]
    old = None
    if old_path and os.path.exists(old_path[0]):
        with open(old_path[0], encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        old = list(lines)
        for name, value in variables.items():
            pattern = re.compile(r"^\s*" + re.escape(str(name)) + r"\s*=")
            locs = [i for i, line in enumerate(lines) if pattern.search(line)]
            entry = f"{name}{assignment}{value}"
            if not locs:
                lines.append(entry)
            elif len(locs) == 1:
                lines[locs[0]] = entry
            else:
                raise ValueError(f"Multiple results for {name} found, something is wrong.")
    else:
        lines = [f"{name}{assignment}{value}" for name, value in variables.items()]
    if old != lines:
        with open(new_path, "w", encoding="utf-8") as handle:
            handle.write("".join(f"{line}\n" for line in lines))
    return old


def with_makevars(new, code, path=None, assignment: str = "="):
    if assignment not in _ASSIGNMENTS:
        raise ValueError(f"`assignment` must be one of {_ASSIGNMENTS}")
    if path is None:
        path = makevars_user()
    workdir = tempfile.mkdtemp()
    makevars_file = os.path.join(workdir, "Makevars")

    def body():
        set_makevars(new, path, makevars_file, assignment)
        return force(code)

    try:
        return with_envvar({"R_MAKEVARS_USER": makevars_file}, body)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def local_makevars(new=None, *, path=None, assignment: str = "=", _local_envir=None, **kwargs):
    if assignment not in _ASSIGNMENTS:
        raise ValueError(f"`assignment` must be one of {_ASSIGNMENTS}")
    values = dict(new or {})
    values.update(kwargs)
    if path is None:
        path = makevars_user()
    workdir = tempfile.mkdtemp()
    makevars_file = os.path.join(workdir, "Makevars")
    current(_local_envir).add(lambda: shutil.rmtree(workdir, ignore_errors=True))
    local_envvar({"R_MAKEVARS_USER": makevars_file}, _local_envir=_local_envir)
    return set_makevars(values, path, makevars_file, assignment)
