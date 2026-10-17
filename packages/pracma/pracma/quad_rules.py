"""Newton-Cotes, Romberg, and one-panel Gauss-Kronrod rules."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import linspace

_EPS = np.finfo(float).eps


def cotes(f, a, b, n=20, nodes=5, **kwargs):
    if nodes < 2 or nodes > 8:
        raise PracmaError("Number of nodes, 'nodes', must be between 2 and 8.")
    if n < nodes:
        raise PracmaError("Argument 'n' must be greater or equal to the number of nodes.")
    fun = _callable(f)

    def wrapped(x):
        return fun(x, **kwargs)

    span = float(nodes) - 1.0
    panels = int(round(span * math.ceil(float(n) / span)))
    count = panels + 1
    x = linspace(a, b, count)
    try:
        g = np.asarray(wrapped(x), dtype=float).reshape(-1)
    except (TypeError, ValueError):
        g = np.array([], dtype=float)
    if g.size != count:
        g = np.array([_one(wrapped(x[i])) for i in range(count)], dtype=float)
    h = float(x[1] - x[0])
    endpts = g[0] + g[panels]
    rule = int(np.trunc(nodes)) - 1
    if rule == 1:
        total = (h / 2.0) * (endpts + 2.0 * np.sum(g[1:panels]))
    elif rule == 2:
        total = (h / 3.0) * (endpts + 4.0 * _sum_seq(g, 2, panels, 2) + 2.0 * _sum_seq(g, 3, panels, 2))
    elif rule == 3:
        total = (3.0 * h / 8.0) * (
            endpts
            + 3.0 * np.sum(_at(g, 2, panels, 3) + _at(g, 3, panels, 3))
            + 2.0 * _sum_seq(g, 4, panels, 3)
        )
    elif rule == 4:
        total = (4.0 * h / 90.0) * (
            7.0 * endpts
            + 32.0 * _sum_seq(g, 2, panels, 4)
            + 12.0 * _sum_seq(g, 3, panels, 4)
            + 32.0 * _sum_seq(g, 4, panels, 4)
            + 14.0 * _sum_seq(g, 5, panels, 4)
        )
    elif rule == 5:
        total = (5.0 * h / 288.0) * (
            19.0 * endpts
            + 75.0 * np.sum(_at(g, 2, panels, 5) + _at(g, 5, panels, 5))
            + 50.0 * np.sum(_at(g, 3, panels, 5) + _at(g, 4, panels, 5))
            + 38.0 * _sum_seq(g, 6, panels, 5)
        )
    elif rule == 6:
        total = (6.0 * h / 840.0) * (
            41.0 * endpts
            + 216.0 * np.sum(_at(g, 2, panels, 6) + _at(g, 6, panels, 6))
            + 27.0 * np.sum(_at(g, 3, panels, 6) + _at(g, 5, panels, 6))
            + 272.0 * _sum_seq(g, 4, panels, 6)
            + 82.0 * _sum_seq(g, 7, panels, 6)
        )
    elif rule == 7:
        total = (7.0 * h / 17280.0) * (
            751.0 * endpts
            + 3577.0 * np.sum(_at(g, 2, panels, 7) + _at(g, 7, panels, 7))
            + 1323.0 * np.sum(_at(g, 3, panels, 7) + _at(g, 6, panels, 7))
            + 2989.0 * np.sum(_at(g, 4, panels, 7) + _at(g, 5, panels, 7))
            + 1502.0 * _sum_seq(g, 8, panels, 7)
        )
    else:
        raise PracmaError("Number of nodes, 'nodes', must be between 2 and 8.")
    return np.float64(total)


def romberg(f, a, b, maxit=25, tol=1e-12, **kwargs):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    tol = abs(float(tol))
    if a == b:
        return {"value": np.float64(0.0), "iter": 0, "rel.error": np.float64(0.0)}
    if a > b:
        raise PracmaError("non-numeric argument to binary operator")
    fun = _callable(f)

    def wrapped(x):
        return _one(fun(x, **kwargs))

    if not math.isfinite(wrapped(a)):
        a = a + _EPS * math.copysign(1.0, b - a)
    if not math.isfinite(wrapped(b)):
        b = b - _EPS * math.copysign(1.0, b - a)
    steps = int(maxit)
    table = np.zeros((steps + 1, steps + 1))
    n = 1
    iteration = 0
    err = 1.0
    while err > tol and iteration < steps:
        iteration += 1
        n = 2 * n
        h = (b - a) / n
        total = wrapped(a)
        for i in range(1, n):
            total = total + 2.0 * wrapped(a + h * i)
        total = (total + wrapped(b)) * h / 2.0
        table[iteration, 0] = total
        for k in range(2, iteration + 2):
            j = 2 + iteration - k
            power = 4 ** (k - 1)
            table[j - 1, k - 1] = (power * table[j, k - 2] - table[j - 1, k - 2]) / (power - 1.0)
        err = abs(table[0, iteration] - table[1, iteration - 1])
    return {
        "value": np.float64(table[0, iteration]),
        "iter": int(iteration),
        "rel.error": np.float64(err),
    }


_T15 = np.array(
    [
        -0.9914553711208126,
        -0.9491079123427585,
        -0.8648644233597691,
        -0.7415311855993944,
        -0.5860872354676911,
        -0.4058451513773972,
        -0.2077849550078985,
        0.0,
        0.2077849550078985,
        0.4058451513773972,
        0.5860872354676911,
        0.7415311855993944,
        0.8648644233597691,
        0.9491079123427585,
        0.9914553711208126,
    ]
)
_C15 = np.array(
    [
        0.02293532201052922,
        0.06309209262997855,
        0.1047900103222502,
        0.1406532597155259,
        0.1690047266392679,
        0.1903505780647854,
        0.2044329400752989,
        0.2094821410847278,
        0.2044329400752989,
        0.1903505780647854,
        0.1690047266392679,
        0.1406532597155259,
        0.1047900103222502,
        0.06309209262997855,
        0.02293532201052922,
    ]
)
_C7 = np.array(
    [
        0.1294849661688697,
        0.2797053914892767,
        0.3818300505051189,
        0.4179591836734694,
        0.3818300505051189,
        0.2797053914892767,
        0.1294849661688697,
    ]
)


def gauss_kronrod(f, a, b, **kwargs):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    if not a < b:
        raise PracmaError("a < b is not TRUE")
    fun = _callable(f)

    def wrapped(x):
        return fun(x, **kwargs)

    nodes7 = _T15[np.array([1, 3, 5, 7, 9, 11, 13])]
    x15 = 0.5 * ((b - a) * _T15 + b + a)
    x7 = 0.5 * ((b - a) * nodes7 + b + a)
    y15 = np.asarray(wrapped(x15), dtype=float).reshape(-1)
    y7 = np.asarray(wrapped(x7), dtype=float).reshape(-1)
    gauss7 = np.sum(_C7 * y7)
    kronrod = np.sum(_C15 * y15)
    return {
        "value": np.float64(kronrod * (b - a) / 2.0),
        "rel.error": np.float64(abs(gauss7 - kronrod)),
    }


def _sum_seq(g, start, stop, step):
    return float(np.sum(_at(g, start, stop, step)))


def _at(g, start, stop, step):
    index = _seq_by(start, stop, step)
    if index.size == 0:
        return np.array([], dtype=float)
    return g[index - 1]


def _seq_by(start, stop, step):
    start = int(start)
    stop = int(stop)
    step = int(step)
    if step == 0 or (step > 0 and stop < start) or (step < 0 and stop > start):
        raise PracmaError("wrong sign in 'by' argument")
    return np.arange(start, stop + (1 if step > 0 else -1), step)


def _one(value):
    array = np.asarray(value, dtype=float).reshape(-1)
    return float(array[0])


def _scalar(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(value)
    if array.size != 1 or np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.number):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    return float(array.reshape(-1)[0])


def _callable(fun):
    if not callable(fun):
        raise PracmaError("argument is not a function")
    return fun
