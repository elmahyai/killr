"""Multiple correspondence analysis (MASS mca)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from mass.errors import MassError


def _is_factor(x: Any) -> bool:
    if hasattr(x, "storage") and hasattr(x, "attributes"):
        classes = x.attributes.get("class", [])
        if isinstance(classes, str):
            classes = [classes]
        return "factor" in classes
    return False


def _as_factor(cl: Any) -> tuple[np.ndarray, list[str], list[str] | None]:
    if not _is_factor(cl):
        raise MassError("all variables must be factors")
    levels = [str(lev) for lev in cl.attributes.get("levels", [])]
    codes = np.asarray(cl.values, dtype=int) - 1
    names = cl.attributes.get("names")
    if names is not None:
        names = [str(item) for item in names]
    return codes, levels, names


def _class_ind(codes: np.ndarray, n_levels: int, n: int) -> np.ndarray:
    x = np.zeros((n, n_levels), dtype=float)
    x[np.arange(n), codes] = 1.0
    return x


def _iter_df_columns(df: Any) -> list[tuple[str, Any]]:
    if hasattr(df, "columns") and hasattr(df, "nrows"):
        return list(df.columns)
    if isinstance(df, Mapping):
        return [(str(k), df[k]) for k in df.keys()]
    raise MassError("df must be a data frame")


@dataclass
class Mca:
    rs: np.ndarray
    cs: np.ndarray
    fs: np.ndarray
    d: np.ndarray
    p: int
    call: Any = None


def mca(df: Any, nf: int = 2, abbrev: bool = False, *, _call: Any = None) -> Mca:
    columns = _iter_df_columns(df)
    if not columns or not all(_is_factor(col) for _, col in columns):
        raise MassError("all variables must be factors")

    blocks: list[np.ndarray] = []
    n = 0
    for _name, col in columns:
        codes, levels, _names = _as_factor(col)
        n = codes.shape[0]
        blocks.append(_class_ind(codes, len(levels), n))

    p = len(columns)
    g = np.hstack(blocks)
    dc = g.sum(axis=0)
    scale = np.sqrt(p * dc)
    x = g / scale
    u, s, vh = np.linalg.svd(x, full_matrices=False)
    v = vh.T
    sec = np.arange(1, nf + 1, dtype=int)
    rs = x @ v[:, sec] / p
    inv_scale = 1.0 / scale
    cs = inv_scale[:, None] * v[:, sec]
    fs = u[:, sec] / (p * s[sec])
    return Mca(
        rs=np.asarray(rs, dtype=float),
        cs=np.asarray(cs, dtype=float),
        fs=np.asarray(fs, dtype=float),
        d=np.asarray(s[sec], dtype=float),
        p=p,
        call=_call if _call is not None else {"abbrev": abbrev},
    )
