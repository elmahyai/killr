"""Stratification factor from survival::strata."""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass
class StrataFactor:
    """R factor: integer codes (1-based) and character level labels."""

    codes: list[int | None]
    levels: list[str]

    def __len__(self) -> int:
        return len(self.codes)


def levels(x: StrataFactor) -> list[str]:
    return list(x.levels)


def _is_factor(x: Any) -> bool:
    return isinstance(x, StrataFactor)


def _is_missing_scalar(item: Any) -> bool:
    if item is None:
        return True
    if isinstance(item, float) and math.isnan(item):
        return True
    return False


def _vector_length(x: Any) -> int:
    if isinstance(x, str):
        return 1
    if _is_factor(x):
        return len(x)
    return len(x)


def _is_atomic(x: Any) -> bool:
    if _is_factor(x):
        return True
    if isinstance(x, str):
        return True
    if isinstance(x, (list, tuple)):
        return all(not isinstance(item, (list, tuple, dict)) for item in x)
    return hasattr(x, "__len__") and not isinstance(x, (dict, set))


def _is_plain_list(x: Any) -> bool:
    return isinstance(x, list) and not _is_factor(x)


def _as_factor(x: Any) -> StrataFactor:
    if _is_factor(x):
        return x
    if isinstance(x, str):
        values = [x]
    elif isinstance(x, (list, tuple)):
        values = list(x)
    else:
        try:
            values = list(x)
        except TypeError:
            values = [x]
    if not values:
        return StrataFactor([], [])
    if all(isinstance(item, str) for item in values if not _is_missing_scalar(item)):
        seen: dict[str, None] = {}
        level_list: list[str] = []
        for item in values:
            if _is_missing_scalar(item):
                continue
            text = str(item)
            if text not in seen:
                seen[text] = None
                level_list.append(text)
        codes: list[int | None] = []
        index = {level: code for code, level in enumerate(level_list, start=1)}
        for item in values:
            if _is_missing_scalar(item):
                codes.append(None)
            else:
                codes.append(index[str(item)])
        return StrataFactor(codes, level_list)
    numeric: list[float | None] = []
    for item in values:
        if _is_missing_scalar(item):
            numeric.append(None)
        else:
            numeric.append(float(item))
    uniq = sorted({value for value in numeric if value is not None})
    level_list = [str(int(value)) if value == int(value) else str(value) for value in uniq]
    index: dict[float, int] = {}
    for code, level in enumerate(level_list, start=1):
        key = float(level) if "." in level else int(level)
        index[key] = code
    codes = []
    for item in numeric:
        if item is None:
            codes.append(None)
        else:
            key = int(item) if item == int(item) else item
            codes.append(index[key])
    return StrataFactor(codes, level_list)


def _unclass_factor(x: StrataFactor) -> list[int | None]:
    return list(x.codes)


def _match_call_words(caller: Any, args: tuple[Any, ...]) -> list[str]:
    names: list[str] = []
    for arg in args:
        found = ""
        if caller is not None:
            for name, value in caller.f_locals.items():
                if name.startswith("_") or name == "args":
                    continue
                if value is arg:
                    found = name
                    break
        names.append(found)
    return names


def _format_labels(values: list[str]) -> list[str]:
    return [str(item) for item in values]


def strata(
    *args: Any,
    na_group: bool = False,
    shortlabel: Any = _MISSING,
    sep: str = ", ",
    **named: Any,
) -> StrataFactor:
    """Build a factor whose levels are all combinations of the inputs."""
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    try:
        if named:
            if args:
                raise TypeError("strata() accepts either positional or named arguments, not both")
            names = list(named.keys())
            allf = [named[name] for name in names]
            argname = names
            if shortlabel is _MISSING:
                shortlabel = False
        else:
            allf = list(args)
            if len(allf) == 1 and _is_plain_list(allf[0]):
                allf = list(allf[0])
            nterms = len(allf)
            argname = _match_call_words(caller, tuple(allf))
            if shortlabel is _MISSING:
                shortlabel = all(
                    isinstance(item, str) or _is_factor(item)
                    for item in allf
                )

        nterms = len(allf)
        if not nterms:
            return StrataFactor([], [])

        arglength = [_vector_length(item) for item in allf]
        if any(length != arglength[0] for length in arglength):
            raise ValueError("all arguments must be the same length")
        if not all(_is_atomic(item) for item in allf):
            raise ValueError("all arguments must be vectors")

        what = _as_factor(allf[0])
        levs = [None if code is None else code - 1 for code in _unclass_factor(what)]
        wlab = list(what.levels)
        if na_group and any(code is None for code in what.codes):
            levs = [len(wlab) if item is None else item for item in levs]
            wlab = wlab + ["NA"]

        if shortlabel:
            labs = list(wlab)
        else:
            labs = [f"{argname[0]}={level}" for level in wlab]

        for i in range(1, nterms):
            what = _as_factor(allf[i])
            wlab = list(what.levels)
            wlev = [None if code is None else code - 1 for code in _unclass_factor(what)]
            if na_group and any(item is None for item in wlev):
                wlev = [len(wlab) if item is None else item for item in wlev]
                wlab = wlab + ["NA"]
            if not shortlabel:
                wlab = _format_labels([f"{argname[i]}={level}" for level in wlab])
            width = len(wlab)
            levs = [
                None if left is None or right is None else right + left * width
                for left, right in zip(levs, wlev)
            ]
            expanded: list[str] = []
            for lab in labs:
                for wlab_item in wlab:
                    expanded.append(f"{lab}{sep}{wlab_item}")
            labs = expanded

        levs = [None if item is None else item + 1 for item in levs]
        ulevs = sorted({item for item in levs if item is not None})
        index = {level: code for code, level in enumerate(ulevs, start=1)}
        levs = [None if item is None else index[item] for item in levs]
        labs = [labs[level - 1] for level in ulevs]
        return StrataFactor(levs, labs)
    finally:
        del frame
