"""Paths inside an installed R package."""

from __future__ import annotations

import os
import subprocess

from fs._error import FsError
from fs.path import FsPath, path, path_tidy
from fs.system import file_exists

_LIBRARIES: list[str] | None = None


def _libraries() -> list[str]:
    global _LIBRARIES
    if _LIBRARIES is not None:
        return _LIBRARIES
    home = os.environ.get("R_HOME")
    if not home:
        home = subprocess.check_output(["R", "RHOME"], text=True).strip()
    script = "cat(.libPaths(), sep = '\\n')"
    listed = subprocess.check_output(["Rscript", "-e", script], text=True)
    _LIBRARIES = [line for line in listed.splitlines() if line]
    if not _LIBRARIES:
        _LIBRARIES = [os.path.join(home, "library")]
    return _LIBRARIES


def _find_package(name: str) -> str:
    for library in _libraries():
        candidate = os.path.join(library, name)
        if os.path.isdir(candidate):
            return candidate
    listed = "\n".join(f"  - '{item}'" for item in path_tidy(_libraries()))
    raise FsError(
        f"Can't find package `{name}` in library locations:\n{listed}",
        kind="EEXIST",
    )


def path_package(package, *parts) -> FsPath:
    """Path of a file inside an installed R package.

    ``inst/`` is preferred when that copy exists, matching ``path_package``.
    """
    if not isinstance(package, str):
        raise FsError("`package` must be a character vector of length 1")
    root = _find_package(package)
    if not parts:
        return path_tidy(root)
    top = path(root, *parts)
    inst = path(root, "inst", *parts)
    chosen = []
    for top_path, inst_path, top_ok, inst_ok in zip(top, inst, file_exists(top), file_exists(inst)):
        if inst_ok:
            chosen.append(inst_path)
        elif top_ok:
            chosen.append(top_path)
    if not chosen:
        quoted = ", ".join(f"'{item}'" for item in top)
        raise FsError(f"File(s) {quoted} do not exist", kind="EEXIST")
    return FsPath(chosen)
