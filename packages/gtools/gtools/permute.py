"""Randomly permute a vector (gtools 3.9.5 ``permute``)."""

from __future__ import annotations

import numpy as np


def permute(x):
    """Randomly reorder the elements of ``x`` (R ``sample`` without replacement)."""
    from boot.rng import sample_int

    if isinstance(x, np.ndarray):
        vec = x.reshape(-1)
        n = vec.size
        if n == 0:
            return x.reshape(-1) if x.ndim else x
        idx = np.array(sample_int(n, n, replace=False), dtype=np.intp) - 1
        out = vec.take(idx)
        if x.ndim == 0:
            return out.reshape(())
        return out

    if isinstance(x, str):
        chars = list(x)
        n = len(chars)
        if n == 0:
            return []
        idx = np.array(sample_int(n, n, replace=False), dtype=np.intp) - 1
        return [chars[i] for i in idx]

    if isinstance(x, (list, tuple)):
        seq = list(x)
        n = len(seq)
        if n == 0:
            return seq if isinstance(x, list) else list(seq)
        idx = np.array(sample_int(n, n, replace=False), dtype=np.intp) - 1
        return [seq[i] for i in idx]

    vec = np.asarray([x])
    idx = np.array(sample_int(1, 1, replace=False), dtype=np.intp) - 1
    return vec.take(idx)[0]
