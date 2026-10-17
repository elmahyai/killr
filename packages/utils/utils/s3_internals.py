"""Internal helpers for ``S3methods`` (utils 4.5.0)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Callable

_KNOWN_PACKAGES: dict[str, str] = json.loads(
    (Path(__file__).with_name("known_s3_generics.json")).read_text()
)
_ALL_KNOWN: list[str] = json.loads(
    (Path(__file__).with_name("all_known_s3_generics.json")).read_text()
)

_GROUP_GENERICS = frozenset({"Math", "Ops", "Complex", "Summary", "matrixOps"})


def rmpkg(pkg: str) -> str:
    if pkg.startswith("package:"):
        return pkg[len("package:") :]
    return pkg


def get_known_s3_generics() -> list[str]:
    return list(_ALL_KNOWN)


def defenv_for_s3_registry(genfun: Callable[..., Any]) -> Any:
    env = getattr(genfun, "__r_enclosing_env__", None)
    if env is not None:
        return env
    return getattr(genfun, "__globals__", {})


def _is_methods_dispatch_on() -> bool:
    return False


def _is_ume_call(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "UseMethod":
        if len(node.args) >= 1:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    return ""


def _is_ume_block(body: list[ast.stmt]) -> str:
    for stmt in body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            found = _is_ume_call(stmt.value)
            if found:
                return found
        if isinstance(stmt, ast.If):
            for branch in (stmt.body, stmt.orelse):
                found = _is_ume_block(branch)
                if found:
                    return found
    return ""


def find_generic(fname: str, envir: Any, *, warn_s4only: bool = True) -> str:
    del warn_s4only
    if not exists(fname, mode="function", envir=envir):
        return ""
    func = get_binding(fname, mode="function", envir=envir)
    tagged = getattr(func, "__r_usemethod__", None)
    if isinstance(tagged, str) and tagged:
        return tagged
    try:
        import inspect

        source = ast.parse(inspect.getsource(func))
    except (OSError, TypeError, SyntaxError):
        return ""
    if isinstance(source, ast.Module):
        for node in source.body:
            if isinstance(node, ast.FunctionDef):
                return _is_ume_block(node.body)
    return ""


def known_package_env(generic: str) -> tuple[str, str] | None:
    package = _KNOWN_PACKAGES.get(generic)
    if package is None:
        return None
    return ("namespace", package)


def s3_registry_names(defenv: Any, prefix: str) -> list[str]:
    if isinstance(defenv, tuple) and defenv[0] == "namespace":
        import json
        import subprocess

        package = defenv[1]
        code = (
            "suppressPackageStartupMessages({"
            f"ns <- asNamespace({package!r});"
            "tbl <- ns[['.__S3MethodsTable__.']];"
            "if (is.null(tbl)) character(0) else ls(tbl)"
            "})"
        )
        wrapped = f"cat(jsonlite::toJSON({code}, auto_unbox=TRUE))"
        raw = subprocess.check_output(["Rscript", "--vanilla", "-e", wrapped], text=True)
        names = json.loads(raw)
        return [str(name) for name in names if str(name).startswith(prefix)]
    table = None
    if isinstance(defenv, dict):
        table = defenv.get(".__S3MethodsTable__.")
    elif hasattr(defenv, "_s3_table"):
        table = defenv._s3_table
    if not table:
        return []
    if isinstance(table, dict):
        return [str(name) for name in table.keys() if str(name).startswith(prefix)]
    return []


def exists(name: str, *, mode: str = "any", envir: Any = None) -> bool:
    value = get_binding(name, mode=mode, envir=envir, missing_ok=True)
    if value is _MISSING:
        return False
    if mode == "function":
        return callable(value)
    return True


def get_binding(name: str, *, mode: str = "any", envir: Any = None, missing_ok: bool = False):
    if envir is None:
        raise ValueError("envir is required")
    if hasattr(envir, "get_binding"):
        value = envir.get_binding(name, missing_ok=True)
    elif isinstance(envir, dict):
        value = envir.get(name, _MISSING)
    else:
        value = getattr(envir, name, _MISSING)
    if value is _MISSING:
        if missing_ok:
            return _MISSING
        raise KeyError(name)
    if mode == "function" and not callable(value):
        if missing_ok:
            return _MISSING
        raise KeyError(name)
    return value


class _Missing:
    pass


_MISSING = _Missing()
