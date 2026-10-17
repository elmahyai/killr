"""with_tempfile, local_tempfile, with_tempdir, local_tempdir (R's tempfile.R).

A temporary name is ``pattern`` + 12 hex digits + ``fileext`` in ``tmpdir``
(the system temp directory by default). The name is not created, as with R's
tempfile(). Python passes the paths to ``code`` as keyword arguments named as
in ``new``, where R binds the names in an environment.
"""

from __future__ import annotations

import os
import tempfile
import uuid

from ._gap import gap
from ._scope import current, force
from .directory import with_dir
from .files import _unlink


def _tmp_name(pattern: str = "file", tmpdir=None, fileext: str = "") -> str:
    base = tmpdir if tmpdir is not None else tempfile.gettempdir()
    while True:
        path = os.path.join(base, f"{pattern}{uuid.uuid4().hex[:12]}{fileext}")
        if not os.path.lexists(path):
            return path


def with_tempfile(new, code, pattern: str = "file", tmpdir=None, fileext: str = ""):
    names = [new] if isinstance(new, str) else list(new)
    paths = {name: _tmp_name(pattern, tmpdir, fileext) for name in names}
    try:
        return force_kwargs(code, paths)
    finally:
        for path in paths.values():
            _unlink(path)


def force_kwargs(code, kwargs):
    if not callable(code):
        raise TypeError("code must be a callable that takes the named paths")
    return code(**kwargs)


def local_tempfile(new=None, lines=None, pattern: str = "file", tmpdir=None,
                   fileext: str = "", *, _local_envir=None) -> str:
    if new is not None:
        gap(
            "local_tempfile",
            "the deprecated `new` form binds names in the caller's environment; "
            "use the returned path",
        )
    path = _tmp_name(pattern, tmpdir, fileext)
    if lines is not None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("".join(f"{line}\n" for line in lines))
    current(_local_envir).add(lambda: _unlink(path))
    return path


def _check_clean(clean) -> None:
    if not isinstance(clean, bool):
        raise ValueError("`clean` must be a single TRUE or FALSE")


def with_tempdir(code, clean: bool = True, pattern: str = "file", tmpdir=None,
                 fileext: str = ""):
    _check_clean(clean)
    tmp = _tmp_name(pattern, tmpdir, fileext)
    os.mkdir(tmp)
    try:
        return with_dir(tmp, code)
    finally:
        if clean:
            _unlink(tmp)


def local_tempdir(pattern: str = "file", tmpdir=None, fileext: str = "",
                  clean: bool = True, *, _local_envir=None) -> str:
    _check_clean(clean)
    path = _tmp_name(pattern, tmpdir, fileext)
    os.makedirs(path)
    if clean:
        current(_local_envir).add(lambda: _unlink(path))
    return path
