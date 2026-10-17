"""File queries, R_user_dir, and the private .libPaths closure."""

from __future__ import annotations

import glob
import os
import stat

from backports._values import NA, BackportError, _MISSING, is_na, match_arg

__all__ = [
    "R_user_dir",
    "dir_exists",
    "file_info",
    "file_mode",
    "file_mtime",
    "file_size",
    "lib_paths",
]


class FileRecord:
    def __init__(self, path, size, isdir, mode, mtime, ctime, atime):
        self.path = path
        self.size = size
        self.isdir = isdir
        self.mode = mode
        self.mtime = mtime
        self.ctime = ctime
        self.atime = atime


def file_info(*paths, extra_cols=True):
    records = [_stat_one(path) for path in _flatten(paths)]
    if extra_cols:
        return records
    return records


def file_size(*paths):
    return _column(paths, "size")


def file_mode(*paths):
    return _column(paths, "mode")


def file_mtime(*paths):
    return _column(paths, "mtime")


def _column(paths, name):
    records = file_info(*paths, extra_cols=False)
    values = [getattr(record, name) for record in records]
    if len(paths) == 1 and not isinstance(paths[0], (list, tuple)):
        return values[0] if values else NA
    return values


def dir_exists(paths):
    items = paths if isinstance(paths, (list, tuple)) else [paths]
    flags = []
    for path in items:
        record = _stat_one(path)
        if is_na(record.isdir):
            flags.append(False)
        else:
            flags.append(bool(record.isdir))
    if isinstance(paths, (list, tuple)):
        return flags
    return flags[0] if flags else False


def _flatten(paths):
    flat = []
    for path in paths:
        if isinstance(path, (list, tuple)):
            flat.extend(path)
        else:
            flat.append(path)
    return flat


def _stat_one(path) -> FileRecord:
    if path is None or is_na(path):
        return FileRecord(path, NA, NA, NA, NA, NA, NA)
    text = os.fspath(path)
    try:
        info = os.stat(text, follow_symlinks=True)
    except OSError:
        return FileRecord(text, NA, NA, NA, NA, NA, NA)
    return FileRecord(
        text,
        info.st_size,
        stat.S_ISDIR(info.st_mode),
        info.st_mode & 0o777,
        info.st_mtime,
        info.st_ctime,
        info.st_atime,
    )


def R_user_dir(package, which=("data", "config", "cache")):
    if not isinstance(package, str) or not package:
        raise BackportError("package must be a character string of length 1")
    kind = match_arg(which, ("data", "config", "cache"))
    home = os.path.realpath(os.path.expanduser("~"))
    if kind == "data":
        path = _env("R_USER_DATA_DIR") or _env("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    elif kind == "config":
        path = _env("R_USER_CONFIG_DIR") or _env("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    else:
        path = _env("R_USER_CACHE_DIR") or _env("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    return os.path.join(path, "R", package)


def _env(name) -> str:
    value = os.environ.get(name, "")
    return value if value else ""


def _r_library() -> str:
    home = os.environ.get("R_HOME", "/usr/lib/R")
    return os.path.join(home, "library")


def _r_library_site() -> list[str]:
    raw = os.environ.get(
        "R_LIBS_SITE",
        "/usr/local/lib/R/site-library/:/usr/local/lib/R/site-library:/usr/lib/R/site-library:/usr/lib/R/library",
    )
    return [item for item in raw.split(os.pathsep) if item]


def _make_lib_paths():
    loc: list[str] = []

    def lib_paths(new=_MISSING, include_site=True):
        nonlocal loc
        if new is not _MISSING:
            expanded = []
            incoming = new if isinstance(new, (list, tuple)) else [new]
            for item in incoming:
                expanded.extend(glob.glob(os.path.expanduser(os.fspath(item))))
            paths = list(expanded)
            if include_site:
                paths.extend(_r_library_site())
            paths.append(_r_library())
            kept = []
            for path in paths:
                if os.path.isdir(path):
                    kept.append(os.path.realpath(path).replace("\\", "/"))
            seen = set()
            unique = []
            for path in kept:
                if path not in seen:
                    seen.add(path)
                    unique.append(path)
            loc = unique
        return list(loc)

    return lib_paths


lib_paths = _make_lib_paths()
