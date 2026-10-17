"""``apropos`` — find objects on the search path by (partial) name (utils 4.5.0)."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from utils import s3_internals as s3i
from utils import s3_session as session

_DOT_INTERNALS = frozenset(
    {
        ".subset",
        ".subset2",
        ".getRequiredPackages",
        ".getRequiredPackages2",
        ".formula2varlist",
        ".isMethodsDispatchOn",
        ".row_names_info",
        ".set_row_names",
        ".ArgsEnv",
        ".GenericArgsEnv",
        ".TAOCP1997init",
        ".gt",
        ".gtn",
        ".primTrace",
        ".primUntrace",
        ".Date",
        ".POSIXct",
        ".POSIXlt",
        ".difftime",
        ".cache_class",
        ".popath",
        ".detach",
        ".maskedMsg",
        ".doWrap",
        ".doSortWrap",
        ".amatch_bounds",
        ".amatch_costs",
        ".check_tzones",
        ".encode_numeric_version",
        ".decode_numeric_version",
        ".make_numeric_version",
        ".expand_R_libs_env_var",
        ".kronecker",
        ".packageStartupMessage",
        ".rmpkg",
    }
)

_INTERNAL_NAME = re.compile(r"^\.(?:__|C_|F_)")


class AproposResult(list[str]):
    """Sorted name list; ``where`` holds parallel search-path indices as strings."""

    where: list[str] | None

    def __init__(self, names: list[str], where: list[str] | None = None) -> None:
        super().__init__(names)
        self.where = where


def _r_json(code: str) -> Any:
    wrapped = f"suppressPackageStartupMessages({{cat(jsonlite::toJSON({code}, auto_unbox=TRUE))}})"
    raw = subprocess.check_output(["Rscript", "--vanilla", "-e", wrapped], text=True)
    if raw in ("[]", "{}"):
        return []
    return json.loads(raw)


def _all_ls(*, all_names: bool) -> list[list[str]]:
    stacks = session._active_stack()
    out: list[list[str] | None] = [None] * len(stacks)
    r_paths: list[tuple[int, str]] = []
    flag = "TRUE" if all_names else "FALSE"
    for pos, (path, environ) in enumerate(stacks, start=1):
        if path == ".GlobalEnv" or (environ is not None and not path.startswith("package:")):
            out[pos - 1] = session.ls_on(path, all_names=all_names)
        else:
            r_paths.append((pos, path))
    if r_paths:
        path_literals = ", ".join(repr(path) for _, path in r_paths)
        code = f"lapply(c({path_literals}), function(p) ls(p, all.names={flag}))"
        data = _r_json(code)
        if isinstance(data, list):
            for (pos, _path), names in zip(r_paths, data):
                out[pos - 1] = [str(item) for item in names] if names else []
    return [names if names is not None else [] for names in out]


def _exists_at(pos: int, name: str, *, mode: str) -> bool:
    paths = session.search()
    if pos < 1 or pos > len(paths):
        return False
    path, environ = session._active_stack()[pos - 1]
    if path == ".GlobalEnv" or (environ is not None and not path.startswith("package:")):
        target = environ if environ is not None else session._GLOBAL
        return s3i.exists(name, mode=mode, envir=target)
    code = f"exists({name!r}, where={pos}, mode={mode!r}, inherits=FALSE)"
    wrapped = f'cat(if ({code})) "true" else "false")'
    return subprocess.check_output(["Rscript", "--vanilla", "-e", wrapped], text=True).strip() == "true"


def _match_names(names: list[str], what: str, *, ignore_case: bool) -> list[str]:
    flags = re.IGNORECASE if ignore_case else 0
    return [name for name in names if re.search(what, name, flags)]


def apropos(
    what: str,
    where: bool = False,
    ignore_case: bool = True,
    dot_internals: bool = False,
    mode: str = "any",
) -> AproposResult:
    if not isinstance(what, str):
        raise TypeError("what must be a character string")
    values: list[str] = []
    where_indices: list[str] = []
    check_mode = mode != "any"
    paths = session.search()
    listings = _all_ls(all_names=True)
    for pos in range(1, len(paths) + 1):
        path = paths[pos - 1]
        all_names = listings[pos - 1]
        matched = _match_names(all_names, what, ignore_case=ignore_case)
        matched = [name for name in matched if not _INTERNAL_NAME.match(name)]
        if not dot_internals and path == "package:base":
            matched = [name for name in matched if name not in _DOT_INTERNALS]
        if matched and check_mode:
            matched = [name for name in matched if _exists_at(pos, name, mode=mode)]
        if matched:
            values.extend(matched)
            if where:
                where_indices.extend(str(pos) for _ in matched)
    pairs = sorted(zip(values, where_indices if where else [""] * len(values)), key=lambda item: item[0])
    names = [item[0] for item in pairs]
    if where:
        return AproposResult(names, [item[1] for item in pairs])
    return AproposResult(names)
