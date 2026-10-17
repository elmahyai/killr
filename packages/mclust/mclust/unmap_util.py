"""One-hot encoding of a class vector (``unmap``)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

__all__ = ["unmap"]


def unmap(
    classification: Any,
    groups: Sequence[Any] | None = None,
    noise: Any | None = None,
    **kwargs: Any,
) -> np.ndarray:
    """Build an ``n x k`` matrix of indicators for ``classification``."""
    cls = np.asarray(classification, dtype=object).ravel()
    n = cls.size
    u = _sort_unique(cls.tolist())

    if groups is None:
        groups_vec = list(u)
    else:
        groups_vec = list(np.asarray(groups, dtype=object).ravel())
        if any(_match_one(val, groups_vec) == 0 for val in u):
            raise ValueError("groups incompatible with classification")

    cgroups = [_as_char(g) for g in groups_vec]
    work_groups = list(groups_vec)

    if noise is not None:
        noiz = _match_one(noise, work_groups)
        if noiz == 0:
            raise ValueError("noise incompatible with classification")
        non_noise = [g for g in work_groups if not _same(g, noise)]
        same_noise = [g for g in work_groups if _same(g, noise)]
        work_groups = non_noise + same_noise

    level_order = _unique_preserve(cgroups)
    group_codes = np.array([_factor_code(c, level_order) for c in cgroups], dtype=int)
    class_codes = np.array([_factor_code(_as_char(c), level_order) for c in cls], dtype=int)

    k = len(group_codes)

    z = np.zeros((n, k), dtype=float)
    for j in range(k):
        z[class_codes == group_codes[j], j] = 1.0
    return z


def _sort_unique(values: list[Any]) -> list[Any]:
    uniq: list[Any] = []
    seen: set[str] = set()
    for item in values:
        key = _as_char(item)
        if key not in seen:
            seen.add(key)
            uniq.append(item)
    if uniq and all(_is_numeric_like(v) for v in uniq):
        return sorted(uniq, key=lambda v: float(v))
    if uniq and all(isinstance(v, (str, np.str_)) for v in uniq):
        return sorted(uniq, key=str)
    return sorted(uniq, key=_as_char)


def _unique_preserve(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _factor_code(label: str, levels: list[str]) -> int:
    try:
        return levels.index(label) + 1
    except ValueError as exc:
        raise ValueError("groups incompatible with classification") from exc


def _match_one(value: Any, container: Sequence[Any]) -> int:
    for i, item in enumerate(container, start=1):
        if _same(item, value):
            return i
    return 0


def _same(a: Any, b: Any) -> bool:
    if _is_numeric_like(a) and _is_numeric_like(b):
        return float(a) == float(b)
    return _as_char(a) == _as_char(b)


def _is_numeric_like(value: Any) -> bool:
    return isinstance(value, (int, np.integer, float, np.floating)) and not isinstance(
        value, (bool, np.bool_)
    )


def _as_char(value: Any) -> str:
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)
