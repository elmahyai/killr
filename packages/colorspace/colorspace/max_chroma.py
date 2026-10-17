"""Maximum HCL chroma for hue and luminance (colorspace 2.1-4)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

_EPS = 1e-8


@lru_cache(maxsize=1)
def _max_chroma_table() -> np.ndarray:
    path = Path(__file__).resolve().parent / "max_chroma_table.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    table = np.zeros((361, 101), dtype=np.float64)
    for key, value in raw.items():
        h_str, l_str = key.split("-", 1)
        table[int(h_str), int(l_str)] = float(value)
    return table


def max_chroma(h, l, floor=False):
    """Approximate maximum chroma for hue ``h`` and luminance ``l`` in HCL."""
    h_arr = np.asarray(h, dtype=np.float64)
    l_arr = np.asarray(l, dtype=np.float64)
    if h_arr.ndim == 0:
        h_arr = h_arr.reshape(1)
    else:
        h_arr = h_arr.ravel()
    if l_arr.ndim == 0:
        l_arr = l_arr.ravel()
    else:
        l_arr = l_arr.ravel()

    n = max(h_arr.size, l_arr.size)
    h_arr = np.resize(h_arr, n)
    l_arr = np.resize(l_arr, n)

    out = h_arr * 0.0 + l_arr * 0.0
    ok = ~np.isnan(out)
    if not np.any(ok):
        return out

    h_work = h_arr[ok].copy()
    l_work = l_arr[ok].copy()

    while np.any(h_work < 0):
        h_work = np.where(h_work < 0, h_work + 360.0, h_work)
    while np.any(h_work >= 360):
        h_work = np.where(h_work >= 360, h_work - 360.0, h_work)

    l_work = np.minimum(100.0, np.maximum(0.0, l_work))

    hmin = np.floor(h_work + _EPS)
    hmax = np.ceil(h_work + _EPS)
    lmin = np.floor(l_work + _EPS)
    lmax = np.ceil(l_work + _EPS)

    hi = hmin.astype(np.int64)
    ha = hmax.astype(np.int64)
    li = lmin.astype(np.int64)
    la = lmax.astype(np.int64)

    table = _max_chroma_table()
    wh = hmax - h_work
    wl = lmax - l_work
    bh = h_work - hmin
    bl = l_work - lmin

    def _sample(h_idx, l_idx):
        values = np.full(h_idx.shape, np.nan, dtype=np.float64)
        valid = (
            (h_idx >= 0)
            & (h_idx <= 360)
            & (l_idx >= 0)
            & (l_idx <= 100)
        )
        values[valid] = table[h_idx[valid], l_idx[valid]]
        return values

    chroma = (
        wh * wl * _sample(hi, li)
        + wh * bl * _sample(hi, la)
        + bh * wl * _sample(ha, li)
        + bh * bl * _sample(ha, la)
    )
    chroma = np.asarray(chroma, dtype=np.float64)
    chroma[(l_work <= 0) | (l_work >= 100)] = 0.0
    if floor:
        chroma = np.floor(chroma)

    out[ok] = chroma
    return out
