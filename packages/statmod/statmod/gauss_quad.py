"""Nodes and weights for Gaussian quadrature.

Translated from statmod 1.5.2. The nodes are the eigenvalues of the
Jacobi matrix, and the weights use the first eigenvector components.
The tridiagonal step is the implicit QL method in src/gaussq2.f.
"""

from __future__ import annotations

import math

import numpy as np

_KINDS = (
    "legendre",
    "chebyshev1",
    "chebyshev2",
    "hermite",
    "jacobi",
    "laguerre",
)


def gauss_quad(n, kind="legendre", alpha=0, beta=0):
    """Nodes and weights for Gaussian quadrature.

    ``kind`` is one of legendre, chebyshev1, chebyshev2, hermite, jacobi,
    or laguerre. A unique prefix is accepted. ``alpha`` and ``beta`` are
    the Jacobi parameters, and ``alpha`` is also the Laguerre parameter.
    """
    count = _as_n(n)
    if count == 0:
        empty = np.zeros(0, dtype=float)
        return {"nodes": empty, "weights": empty.copy()}
    rule = _match_arg(kind, _KINDS)
    alpha = _as_float(alpha)
    beta = _as_float(beta)
    diagonal, subdiagonal, log_mu = _coefficients(count, rule, alpha, beta)
    first = np.zeros(count, dtype=float)
    first[0] = 1.0
    nodes, lead, _ierr = _gausq2(diagonal, subdiagonal, first)
    weights = np.exp(log_mu + 2.0 * np.log(np.abs(lead)))
    return {
        "nodes": np.asarray(nodes, dtype=float),
        "weights": np.asarray(weights, dtype=float),
    }


def _as_n(n):
    """R ``as.integer`` followed by the sign test in ``gauss.quad``."""
    if isinstance(n, bool):
        number = int(n)
    elif isinstance(n, (int, np.integer)):
        number = int(n)
    elif isinstance(n, (float, np.floating)):
        if not math.isfinite(float(n)):
            raise ValueError("missing value where TRUE/FALSE needed")
        number = int(math.trunc(float(n)))
    elif n is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    elif isinstance(n, (list, tuple, np.ndarray)):
        array = np.asarray(n)
        if array.size == 0:
            raise ValueError("argument is of length zero")
        if array.size > 1:
            raise ValueError("the condition has length > 1")
        return _as_n(array.reshape(-1)[0].item())
    else:
        raise ValueError("invalid 'n' argument")
    if number < -2147483648 or number > 2147483647:
        raise ValueError("missing value where TRUE/FALSE needed")
    if number < 0:
        raise ValueError("need non-negative number of nodes")
    return number


def _as_float(value):
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (list, tuple, np.ndarray)):
        array = np.asarray(value, dtype=float)
        if array.size != 1:
            raise ValueError("alpha and beta must have length 1")
        return float(array.reshape(-1)[0])
    return float(value)


def _match_arg(arg, choices):
    """R ``match.arg``. An ambiguous prefix is the same error as a miss."""
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple, np.ndarray)):
        values = [None if item is None else str(item) for item in np.asarray(arg, dtype=object).reshape(-1).tolist()]
        if values == list(choices):
            return choices[0]
        if len(values) != 1:
            raise ValueError("'arg' must be of length 1")
        return _match_arg(values[0], choices)
    if not isinstance(arg, str):
        raise ValueError("'arg' must be NULL or a character vector")
    if arg in choices:
        return arg
    hits = [choice for choice in choices if choice.startswith(arg)]
    if len(hits) == 1:
        return hits[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise ValueError(f"'arg' should be one of {quoted}")


def _coefficients(n, kind, alpha, beta):
    index = np.arange(1, n + 1, dtype=float)
    lower = index[:-1]
    if kind == "legendre":
        log_mu = math.log(2.0)
        diagonal = np.zeros(n, dtype=float)
        sub = lower / np.sqrt(4.0 * lower * lower - 1.0)
    elif kind == "chebyshev1":
        log_mu = math.log(math.pi)
        diagonal = np.zeros(n, dtype=float)
        sub = np.full(n - 1, 0.5, dtype=float)
        if n == 1:
            sub = np.array([math.sqrt(0.5)], dtype=float)
        else:
            sub[0] = math.sqrt(0.5)
    elif kind == "chebyshev2":
        log_mu = math.log(math.pi / 2.0)
        diagonal = np.zeros(n, dtype=float)
        sub = np.full(max(n - 1, 0), 0.5, dtype=float)
    elif kind == "hermite":
        log_mu = math.log(math.pi) / 2.0
        diagonal = np.zeros(n, dtype=float)
        sub = np.sqrt(lower / 2.0)
    elif kind == "jacobi":
        both = alpha + beta
        log_mu = (
            (both + 1.0) * math.log(2.0)
            + math.lgamma(alpha + 1.0)
            + math.lgamma(beta + 1.0)
            - math.lgamma(both + 2.0)
        )
        diagonal = np.empty(n, dtype=float)
        diagonal[0] = (beta - alpha) / (both + 2.0)
        if n > 1:
            upper = np.arange(2, n + 1, dtype=float)
            step = both + 2.0 * upper
            diagonal[1:] = (beta * beta - alpha * alpha) / (step - 2.0) / step
        first = math.sqrt(
            4.0
            * (alpha + 1.0)
            * (beta + 1.0)
            / (both + 2.0) ** 2
            / (both + 3.0)
        )
        if n == 1:
            sub = np.array([first], dtype=float)
        else:
            sub = np.empty(n - 1, dtype=float)
            sub[0] = first
            if n > 2:
                upper = np.arange(2, n, dtype=float)
                step = both + 2.0 * upper
                sub[1:] = np.sqrt(
                    4.0
                    * upper
                    * (upper + alpha)
                    * (upper + beta)
                    * (upper + both)
                    / (step * step - 1.0)
                    / (step * step)
                )
    elif kind == "laguerre":
        diagonal = 2.0 * index - 1.0 + alpha
        sub = np.sqrt(lower * (lower + alpha))
        log_mu = math.lgamma(alpha + 1.0)
    else:
        raise ValueError(kind)
    sub = np.concatenate([np.asarray(sub, dtype=float).reshape(-1), np.array([0.0])])
    return np.asarray(diagonal, dtype=float), sub, log_mu


def _gausq2(diagonal, subdiagonal, first):
    """Implicit QL method from ``gausq2``.

    Returns the eigenvalues in ascending order and the first components
    of the orthonormal eigenvectors. ``n == 1`` returns the inputs.
    """
    n = len(diagonal)
    d = [0.0] * (n + 1)
    e = [0.0] * (n + 1)
    z = [0.0] * (n + 1)
    for i in range(1, n + 1):
        d[i] = float(diagonal[i - 1])
        e[i] = float(subdiagonal[i - 1])
        z[i] = float(first[i - 1])
    machep = 2.0 ** (-52.0)
    ierr = 0
    if n == 1:
        return d[1:], z[1:], ierr
    e[n] = 0.0
    for level in range(1, n + 1):
        sweeps = 0
        while True:
            end = level
            for end in range(level, n + 1):
                if end == n:
                    break
                if abs(e[end]) <= machep * (abs(d[end]) + abs(d[end + 1])):
                    break
            pivot = d[level]
            if end == level:
                break
            if sweeps == 30:
                ierr = level
                return d[1:], z[1:], ierr
            sweeps += 1
            shift = (d[level + 1] - pivot) / (2.0 * e[level])
            radius = math.sqrt(shift * shift + 1.0)
            shift = d[end] - pivot + e[level] / (shift + math.copysign(radius, shift))
            sine = 1.0
            cosine = 1.0
            pivot = 0.0
            for step in range(1, end - level + 1):
                row = end - step
                f = sine * e[row]
                b = cosine * e[row]
                if abs(f) < abs(shift):
                    sine = f / shift
                    radius = math.sqrt(sine * sine + 1.0)
                    e[row + 1] = shift * radius
                    cosine = 1.0 / radius
                    sine = sine * cosine
                else:
                    cosine = shift / f
                    radius = math.sqrt(cosine * cosine + 1.0)
                    e[row + 1] = f * radius
                    sine = 1.0 / radius
                    cosine = cosine * sine
                shift = d[row + 1] - pivot
                radius = (d[row] - shift) * sine + 2.0 * cosine * b
                pivot = sine * radius
                d[row + 1] = shift + pivot
                shift = cosine * radius - b
                f = z[row + 1]
                z[row + 1] = sine * z[row] + cosine * f
                z[row] = cosine * z[row] - sine * f
            d[level] = d[level] - pivot
            e[level] = shift
            e[end] = 0.0
    for second in range(2, n + 1):
        place = second - 1
        chosen = place
        smallest = d[place]
        for candidate in range(second, n + 1):
            if d[candidate] >= smallest:
                continue
            chosen = candidate
            smallest = d[candidate]
        if chosen == place:
            continue
        d[chosen] = d[place]
        d[place] = smallest
        saved = z[place]
        z[place] = z[chosen]
        z[chosen] = saved
    return d[1:], z[1:], ierr
