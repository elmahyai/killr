"""Search-path simulation for ``S3methods`` when ``use_env`` is true."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from utils.s3_internals import rmpkg


class BindingEnviron:
    """Environment stand-in whose attach name is always ``envir``."""

    def __init__(self, bindings: dict[str, Any] | None = None) -> None:
        self._bindings = dict(bindings or {})

    def get_binding(self, name: str, *, missing_ok: bool = False) -> Any:
        if name in self._bindings:
            return self._bindings[name]
        if missing_ok:
            from utils.s3_internals import _MISSING

            return _MISSING
        raise KeyError(name)

    def ls(self, *, all_names: bool = False) -> list[str]:
        names = list(self._bindings.keys())
        if not all_names:
            names = [name for name in names if not name.startswith(".")]
        return names


_GLOBAL = BindingEnviron()
_SESSION: list[tuple[str, Any]] | None = None


def parent_frame() -> BindingEnviron:
    return _GLOBAL


def _default_search() -> list[str]:
    return [
        ".GlobalEnv",
        "package:stats",
        "package:graphics",
        "package:grDevices",
        "package:utils",
        "package:datasets",
        "package:methods",
        "Autoloads",
        "package:base",
    ]


def _active_stack() -> list[tuple[str, Any]]:
    if _SESSION is not None:
        return _SESSION
    return [(name, _GLOBAL if name == ".GlobalEnv" else None) for name in _default_search()]


def search() -> list[str]:
    return [name for name, _ in _active_stack()]


def attach(environ: Any, *, pos: int = 2, name: str = "envir") -> None:
    global _SESSION
    if _SESSION is None:
        _SESSION = [(name, _GLOBAL if name == ".GlobalEnv" else None) for name in _default_search()]
    index = max(0, min(len(_SESSION), int(pos) - 1))
    _SESSION.insert(index, (name, environ))


def detach(pos: int = 2) -> None:
    global _SESSION
    if _SESSION is None:
        return
    index = int(pos) - 1
    if 0 <= index < len(_SESSION):
        del _SESSION[index]


def _r_ls(path: str, *, all_names: bool) -> list[str]:
    code = (
        "suppressPackageStartupMessages({"
        f"cat(jsonlite::toJSON(ls({path!r}, all.names={'TRUE' if all_names else 'FALSE'}), auto_unbox=TRUE))"
        "})"
    )
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", code], text=True)
    if raw == "[]" or raw == "{}":
        return []
    data = json.loads(raw)
    if isinstance(data, list):
        return [str(item) for item in data]
    return []


def ls_on(path: str, *, all_names: bool = False) -> list[str]:
    for name, environ in _active_stack():
        if name != path:
            continue
        if path == ".GlobalEnv":
            target = environ if environ is not None else _GLOBAL
            if hasattr(target, "ls"):
                return target.ls(all_names=all_names)
            if isinstance(target, dict):
                names = list(target.keys())
                if not all_names:
                    names = [item for item in names if not item.startswith(".")]
                return names
            return []
        if path.startswith("package:"):
            return _r_ls(path, all_names=all_names)
        if environ is not None and hasattr(environ, "ls"):
            return environ.ls(all_names=all_names)
        if isinstance(environ, dict):
            names = list(environ.keys())
            if not all_names:
                names = [item for item in names if not item.startswith(".")]
            return names
        return []
    if path.startswith("package:"):
        return _r_ls(path, all_names=all_names)
    return []


def collect_objects(*, all_names: bool, drop_path: bool, use_env: bool) -> tuple[list[str], list[str]]:
    paths = search()
    if drop_path:
        keep = [0, 1, len(paths) - 1] if use_env else [0, len(paths) - 1]
        paths = [paths[index] for index in keep if 0 <= index < len(paths)]
    names: list[str] = []
    sources: list[str] = []
    seen: set[str] = set()
    for path in paths:
        for name in ls_on(path, all_names=all_names):
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
            sources.append(rmpkg(path))
    return names, sources


def loaded_namespaces() -> list[str]:
    code = "cat(jsonlite::toJSON(loadedNamespaces(), auto_unbox=TRUE))"
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", code], text=True)
    data = json.loads(raw)
    return [str(item) for item in data]


def namespace_s3_table(package: str, pattern: str, *, all_names: bool) -> list[str]:
    code = (
        "suppressPackageStartupMessages({"
        "ns <- getNamespace(%r);"
        "tbl <- ns[['.__S3MethodsTable__.']];"
        "if (is.null(tbl)) character(0) else ls(tbl, pattern=%r, all.names=%s)"
        "})" % (package, pattern, "TRUE" if all_names else "FALSE")
    )
    wrapped = f"cat(jsonlite::toJSON({code}, auto_unbox=TRUE))"
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", wrapped], text=True)
    data = json.loads(raw)
    if not data:
        return []
    return [str(item) for item in data]


def find_function(name: str) -> list[str]:
    code = (
        "suppressPackageStartupMessages({"
        f"where <- find({name!r}, mode='function');"
        "cat(jsonlite::toJSON(where, auto_unbox=TRUE))"
        "})"
    )
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", code], text=True)
    data = json.loads(raw)
    if not data:
        return []
    return [str(item) for item in data]


def exists_in_search(name: str, *, mode: str = "function") -> bool:
    from utils.s3_internals import _MISSING

    for path, environ in _active_stack():
        if path == ".GlobalEnv" or not path.startswith("package:"):
            target = environ if environ is not None else _GLOBAL
            if hasattr(target, "get_binding"):
                value = target.get_binding(name, missing_ok=True)
                if value is not _MISSING and (mode != "function" or callable(value)):
                    return True
            elif isinstance(target, dict):
                value = target.get(name, _MISSING)
                if value is not _MISSING and (mode != "function" or callable(value)):
                    return True
            if path == ".GlobalEnv" or not path.startswith("package:"):
                continue
        if path.startswith("package:"):
            code = (
                f"cat(if (exists({name!r}, where={path!r}, mode={mode!r}, "
                f"inherits=FALSE)) 'true' else 'false')"
            )
            if subprocess.check_output(["Rscript", "--vanilla", "-e", code], text=True).strip() == "true":
                return True
    return False


def find_generic_in_path(name: str, where: str) -> str:
    code = (
        "suppressPackageStartupMessages({"
        "utils:::findGeneric(%r, envir=as.environment(%r), warnS4only=FALSE)"
        "})" % (name, where)
    )
    wrapped = f"cat(jsonlite::toJSON({code}, auto_unbox=TRUE))"
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", wrapped], text=True)
    value = json.loads(raw)
    return str(value) if value else ""
