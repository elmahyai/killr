"""List S3 methods for a generic or class (``utils:::.S3methods`` in R 4.5.0)."""

from __future__ import annotations

import re
import subprocess
import warnings
from dataclasses import dataclass
from typing import Any

from tools.nons3 import non_s3_methods

from utils import s3_internals as s3i
from utils import s3_session as session


@dataclass
class _MethodRow:
    name: str
    visible: bool
    source: str
    generic: str
    is_s4: bool = False


class MethodsFunction(list):
    """Character vector of method names with R ``MethodsFunction`` metadata."""

    def __init__(self, rows: list[_MethodRow], *, byclass: bool) -> None:
        super().__init__(row.name for row in rows)
        self.info = rows
        self.byclass = byclass


def _rbind_some(rows: list[_MethodRow], names: list[str], msg: str) -> list[_MethodRow]:
    unique = list(dict.fromkeys(names))
    existing = {row.name: row for row in rows}
    out = list(rows)
    for name in unique:
        if name in existing:
            continue
        out.append(_MethodRow(name=name, visible=False, source=msg, generic="", is_s4=False))
    return out


def _is_local_environ(envir: Any) -> bool:
    return hasattr(envir, "get_binding") or isinstance(envir, dict)


def _delegate_r(
    generic_function: str | None,
    class_: str | None,
    envir: Any,
    all_names: bool,
    drop_path: bool,
    use_env: bool,
) -> MethodsFunction:
    parts = ["suppressPackageStartupMessages(library(utils))", "res <- utils:::.S3methods("]
    args: list[str] = []
    if generic_function is not None:
        args.append(f"generic.function={generic_function!r}")
    if class_ is not None:
        args.append(f"class={class_!r}")
    args.append(f"all.names={'TRUE' if all_names else 'FALSE'}")
    args.append(f"dropPath={'TRUE' if drop_path else 'FALSE'}")
    args.append(f"useEnv={'TRUE' if use_env else 'FALSE'}")
    parts.append(", ".join(args))
    parts.append(")")
    parts.append("info <- attr(res, 'info')")
    parts.append(
        "cat(jsonlite::toJSON(list("
        "names=unname(res), "
        "byclass=attr(res, 'byclass'), "
        "visible=info$visible, "
        "from=info$from, "
        "generic=info$generic, "
        "isS4=info$isS4"
        "), auto_unbox=TRUE))"
    )
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", "".join(parts)], text=True)
    import json

    payload = json.loads(raw)
    rows = [
        _MethodRow(
            name=str(name),
            visible=bool(payload["visible"][index]),
            source=str(payload["from"][index]),
            generic=str(payload["generic"][index]),
            is_s4=bool(payload["isS4"][index]),
        )
        for index, name in enumerate(payload["names"])
    ]
    return MethodsFunction(rows, byclass=bool(payload["byclass"]))


def S3methods(
    generic_function: str | None = None,
    class_: str | None = None,
    envir: Any | None = None,
    all_names: bool = False,
    drop_path: bool = False,
    use_env: bool = False,
) -> MethodsFunction:
    """Return S3 method names for ``generic_function`` or ``class_``."""
    if generic_function is None and class_ is None:
        raise ValueError("must supply 'generic.function' or 'class'")
    if envir is None:
        envir = session.parent_frame()
    if not use_env or not _is_local_environ(envir):
        return _delegate_r(generic_function, class_, envir, all_names, drop_path, use_env)

    stop_list = set(non_s3_methods(None))
    known_generics = s3i.get_known_s3_generics()
    attached = False
    if use_env:
        session.attach(envir, pos=2, name="envir")
        attached = True
    try:
        names, sources = session.collect_objects(
            all_names=all_names,
            drop_path=drop_path,
            use_env=use_env,
        )
        rows = [
            _MethodRow(name=name, visible=True, source=source, generic="", is_s4=False)
            for name, source in zip(names, sources, strict=True)
        ]

        if generic_function is not None:
            if not isinstance(generic_function, str):
                generic_function = str(generic_function)
            if (
                not s3i.exists(generic_function, mode="function", envir=envir)
                and generic_function not in s3i._GROUP_GENERICS
            ):
                raise ValueError(f"no function '{generic_function}' is visible")
            true_gf = generic_function
            if generic_function not in known_generics:
                true_gf = s3i.find_generic(generic_function, envir, warn_s4only=True)
                if not true_gf:
                    true_gf = generic_function
                elif true_gf != generic_function:
                    warnings.warn(
                        f"generic function '{generic_function}' dispatches methods for generic '{true_gf}'",
                        stacklevel=2,
                    )
                    generic_function = true_gf
            prefix = f"{generic_function}."
            rows = [row for row in rows if row.name.startswith(prefix)]
            rows = [row for row in rows if row.name not in stop_list]
            rows = [row for row in rows if session.exists_in_search(row.name, mode="function")]
            defenv = s3i.known_package_env(generic_function)
            if defenv is None:
                genfun = s3i.get_binding(generic_function, mode="function", envir=envir)
                defenv = s3i.defenv_for_s3_registry(genfun)
            registry = s3i.s3_registry_names(defenv, prefix)
            if registry:
                rows = _rbind_some(
                    rows,
                    registry,
                    f"registered S3method for {generic_function}",
                )
            if generic_function == "all":
                rows = [row for row in rows if not row.name.startswith("all.equal")]
            for row in rows:
                row.generic = generic_function
        else:
            if not isinstance(class_, str):
                class_ = str(class_)
            if class_ is None:
                raise ValueError("must supply 'generic.function' or 'class'")
            if "," in class_:
                class_ = class_.split(",")[0]
            pattern = re.escape(f".{class_}$")
            rows = [row for row in rows if re.search(pattern, row.name)]
            rows = [row for row in rows if row.name not in stop_list]
            kept: list[_MethodRow] = []
            for row in rows:
                possible = re.sub(pattern, "", row.name)
                if possible in known_generics:
                    kept.append(row)
                    continue
                where = session.find_function(possible)
                if not where:
                    continue
                if any(
                    session.find_generic_in_path(possible, path)
                    for path in where
                ):
                    kept.append(row)
            rows = kept
            reg_pattern = f".{class_}$"
            registered: list[str] = []
            for package in session.loaded_namespaces():
                registered.extend(
                    session.namespace_s3_table(package, reg_pattern, all_names=all_names)
                )
            if registered:
                registered = [
                    name
                    for name in registered
                    if session.exists_in_search(
                        re.sub(reg_pattern, "", name),
                        mode="function",
                    )
                ]
            if registered:
                rows = _rbind_some(rows, registered, "registered S3method")
            for row in rows:
                row.generic = re.sub(pattern, "", row.name)

        rows.sort(key=lambda row: row.name)
        return MethodsFunction(rows, byclass=generic_function is None)
    finally:
        if attached:
            session.detach(2)
