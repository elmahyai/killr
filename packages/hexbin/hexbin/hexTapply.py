"""Apply a function to the data of each cell. Ported from hexbin 1.28.6 `hexTapply` in R/hexutil.R.

R's `tapply` returns a named vector keyed by the cell ids. This returns a dict with the
same names as keys, in ascending id order. Each group keeps the order of the points, as
R's `split` does. With `simplify=False` each value is a one-element list, as R's list-array
result has them.

The builtins `sum`, `min`, `max` and `len` reduce every group in one vectorized pass.
Any other FUN is called once per group.
"""

from __future__ import annotations

import builtins

import numpy as np

from ._classes import HexBin, NA_INTEGER

_REDUCEAT = {builtins.sum: np.add, builtins.min: np.minimum, builtins.max: np.maximum}


def hexTapply(hbin: HexBin, dat, FUN=builtins.sum, *args, simplify: bool = True, **kwargs) -> dict:
    if hbin.cID is None:
        raise ValueError(
            "Must have cell ID's to do this operation \n\n"
            "          please re-bin data using IDs = TRUE"
        )
    dat = np.asarray(dat)
    ids = np.asarray(hbin.cID)
    if dat.size > 0 and dat.size != ids.size:
        raise ValueError("Length of IDs does not match the length of the data")

    keep = ids != NA_INTEGER
    ids_k = ids[keep]
    dat_k = dat[keep]

    order = np.argsort(ids_k, kind="stable")
    sorted_ids = ids_k[order]
    sorted_dat = dat_k[order]
    levels, starts = np.unique(sorted_ids, return_index=True)
    bounds = np.append(starts, sorted_ids.size)

    if not args and not kwargs and (FUN is len or FUN in _REDUCEAT):
        if FUN is len:
            results = np.diff(bounds)
        else:
            results = _REDUCEAT[FUN].reduceat(sorted_dat, starts)
        values = list(results.tolist())
    else:
        values = []
        for i in range(levels.size):
            group = sorted_dat[bounds[i] : bounds[i + 1]]
            values.append(FUN(group, *args, **kwargs))

    out: dict = {}
    for level, result in zip(levels.tolist(), values):
        out[int(level)] = result if simplify else [result]
    return out
