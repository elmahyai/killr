"""Confidence limits for Poisson rates, from survival::cipoisson."""

import numpy as np

from survival.gamma import qgamma
from survival.norm import qnorm


def _match_method(method):
    choices = ("exact", "anscombe")
    if isinstance(method, (list, tuple)) and list(method) == list(choices):
        return choices[0]
    text = method[0] if isinstance(method, (list, tuple)) else method
    if text in choices:
        return text
    hits = [choice for choice in choices if choice.startswith(str(text))]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"'{text}' is not a valid method")


def _recycle(*arrays):
    lengths = [len(np.atleast_1d(arr)) for arr in arrays]
    nn = max(lengths)
    out = []
    for arr, length in zip(arrays, lengths):
        flat = np.atleast_1d(arr).reshape(-1)
        if nn > 1 and length < nn:
            flat = np.resize(flat, nn)
        elif length > nn:
            flat = flat[:nn]
        out.append(flat)
    return nn, out


def cipoisson(k, time=1, p=0.95, method=("exact", "anscombe")):
    """Two-sided confidence limits for a Poisson rate."""
    nn, (k_vec, time_vec, p_vec) = _recycle(k, time, p)
    method = _match_method(method)
    tail = (1.0 - np.asarray(p_vec, dtype=float)) / 2.0

    if method == "exact":
        lower = np.array(
            [
                0.0 if kval == 0 else qgamma(float(prob), float(kval if kval != 0 else 1.0))
                for prob, kval in zip(tail, k_vec)
            ],
            dtype=float,
        )
        upper = np.array(
            [qgamma(1.0 - float(prob), float(kval + 1.0)) for prob, kval in zip(tail, k_vec)],
            dtype=float,
        )
    elif method == "anscombe":
        z = [qnorm(float(prob)) for prob in tail]
        z = np.asarray(z, dtype=float)
        upper = (np.sqrt(k_vec + 7.0 / 8.0) - z / 2.0) ** 2
        lower = (np.sqrt(k_vec - 1.0 / 8.0) + z / 2.0) ** 2
    else:
        raise ValueError("Invalid method")

    time_vec = np.asarray(time_vec, dtype=float)
    if np.any(time_vec <= 0):
        bad = time_vec <= 0
        lower = np.where(bad, np.nan, lower)
        upper = np.where(bad, np.nan, upper)

    lower = lower / time_vec
    upper = upper / time_vec

    if nn == 1:
        return np.array([lower[0], upper[0]])

    return np.column_stack([lower, upper])
