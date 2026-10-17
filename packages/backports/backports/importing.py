"""import copies backports that are newer than a chosen R version."""

from __future__ import annotations

import sys

from backports._values import BackportError

__all__ = ["get_backports", "import_"]

# Newest first. A version that is already running contributes nothing at or below it.
FUNS = {
    "4.4.0": ["%||%"],
    "4.3.0": ["as.Rconcordance", "matchConcordance"],
    "4.1.0": ["...names", ".libPaths"],
    "4.0.1": ["paste", "paste0"],
    "4.0.0": [
        "R_user_dir",
        "deparse1",
        "list2DF",
        "suppressWarnings",
        "suppressMessages",
        "stopifnot",
    ],
    "3.6.0": [
        "warningCondition",
        "errorCondition",
        "vignetteInfo",
        "dQuote",
        "sQuote",
        "removeSource",
        "asplit",
        "str2lang",
        "str2expression",
    ],
    "3.5.0": ["...length", "...elt", "isFALSE", "isTRUE"],
    "3.4.0": ["hasName", ".valid.factor"],
    "3.3.0": ["startsWith", "endsWith", "strrep", "capture.output"],
    "3.2.0": [
        "anyNA",
        "dir.exists",
        "file.size",
        "file.mode",
        "file.mtime",
        "lengths",
        "file.info",
        "URLencode",
        "isNamespaceLoaded",
        "trimws",
    ],
    "3.1.0": [],
    "3.0.0": [],
    "0.0.0": [],
}


def _version(value) -> tuple:
    return tuple(int(part) for part in str(value).split("."))


def get_backports(v="4.5.0"):
    version = _version(v)
    names = list(FUNS)
    stop = len(names)
    for index, key in enumerate(names):
        if version >= _version(key):
            stop = index
            break
    chosen = []
    for key in names[:stop]:
        chosen.extend(FUNS[key])
    return chosen


def import_(pkgname, obj=None, force=False, version="4.5.0"):
    if obj is None:
        names = get_backports(version)
    else:
        names = list(obj)
        if not force:
            available = set(get_backports(version))
            names = [name for name in names if name in available]
    if names:
        module = sys.modules.get(pkgname)
        if module is None:
            raise BackportError(f"there is no package called {pkgname!r}")
        for name in names:
            value = _object(name)
            setattr(module, name, value)
    return True


def _object(name):
    import backports

    try:
        return backports.BY_R_NAME[name]
    except KeyError as exc:
        raise BackportError(f"object {name!r} not found") from exc
