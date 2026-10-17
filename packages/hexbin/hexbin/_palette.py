"""Shared sampling and hex formatting for the hexbin colour palettes. Helper, not a translated function.

Each R palette is a lookup table of RGB bytes, read at `round(seq(beg, end, length = n))` and
written with `rgb()`. The table is formatted once, at import, by `hex_rows`; a call then only
samples the row indices and looks them up. R rebuilds its table inside every call.
"""

from __future__ import annotations

import numpy as np


def hex_rows(table) -> list[str]:
    """R's `rgb(M[,1]/255, M[,2]/255, M[,3]/255)` for each row of an (rows, 3) table.

    Each channel is `(unsigned int)(255 * x + 0.5)` and is written as uppercase hex.
    """
    arr = np.asarray(table, dtype=np.int64)
    chan = (255 * (arr / 255) + 0.5).astype(np.int64)
    return ["#%02X%02X%02X" % (r, g, b) for r, g, b in chan.tolist()]


def _r_seq_length_out(beg: float, end: float, n: int) -> np.ndarray:
    """R's `seq(beg, end, length = n)` for doubles, the `length.out` branch of seq.default."""
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    if n == 1:
        return np.array([float(beg)])
    if n == 2:
        return np.array([float(beg), float(end)])
    if beg == end:
        return np.full(n, float(beg))
    n1 = n - 1
    step = (end - beg) / n1
    out = np.empty(n, dtype=np.float64)
    out[0] = beg
    out[-1] = end
    out[1:-1] = beg + np.arange(1, n1, dtype=np.float64) * step
    return out


def palette_from_hex(rows: list[str], n: int, beg: float = 1, end: float = 256) -> list[str]:
    """Sample `n` colours from the formatted rows of a palette, as the R palette functions do.

    An index past the last row is an error, as R's rgb() stops on the NA it is given.
    """
    if beg < 1 or end < 1 or beg > 256 or end > 256:
        raise ValueError("`beg' and `end' must be numbers in the interval [1,256]")
    idx = np.rint(_r_seq_length_out(beg, end, n)).astype(np.int64)  # R's round(): half to even
    if idx.size == 1:
        # R's M[idx, ] drops to a plain vector for one row, and the later M[, 1] then fails.
        raise ValueError("incorrect number of dimensions")
    if idx.size and (idx.min() < 1 or idx.max() > len(rows)):
        raise ValueError("color intensity NA, not in [0,1]")
    return [rows[i - 1] for i in idx.tolist()]
