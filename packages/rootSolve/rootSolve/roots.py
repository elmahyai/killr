"""All roots of one equation on an interval.

The scan is rootSolve's. Each sign change is polished by R's zeroin,
which is the Brent method used by uniroot.
"""

import math

_EPS = 2.220446049250313e-16


def _zeroin(ax, bx, fa, fb, func, tol, maxiter):
    a = ax
    b = bx
    c = a
    fc = fa
    left = maxiter + 1
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    while left:
        left -= 1
        prev_step = b - a
        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa
        tol_act = 2.0 * _EPS * abs(b) + tol / 2.0
        new_step = (c - b) / 2.0
        if abs(new_step) <= tol_act or fb == 0.0:
            return b
        if abs(prev_step) >= tol_act and abs(fa) > abs(fb):
            cb = c - b
            if a == c:
                t1 = fb / fa
                p = cb * t1
                q = 1.0 - t1
            else:
                q = fa / fc
                t1 = fb / fc
                t2 = fb / fa
                p = t2 * (cb * q * (q - t1) - (b - a) * (t1 - 1.0))
                q = (q - 1.0) * (t1 - 1.0) * (t2 - 1.0)
            if p > 0.0:
                q = -q
            else:
                p = -p
            if (
                p < (0.75 * cb * q - abs(tol_act * q) / 2.0)
                and p < abs(prev_step * q / 2.0)
            ):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0.0 else -tol_act
        a = b
        fa = fb
        b += new_step
        fb = func(b)
        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
    return b


def _uniroot(func, lower, upper, tol, maxiter):
    fa = float(func(lower))
    fb = float(func(upper))
    return _zeroin(lower, upper, fa, fb, func, tol, maxiter)


def uniroot_all(
    f,
    interval=None,
    lower=None,
    upper=None,
    tol=None,
    maxiter=1000,
    trace=0,
    n=100,
    **kwargs,
):
    """Roots of ``f`` between the endpoints.

    The interval is split into ``n`` pieces. Exact zeros on the grid are
    kept first. Each sign change is then passed to uniroot. ``tol``
    defaults to double epsilon to the power 0.2.
    """
    if interval is not None:
        ends = [float(item) for item in interval]
        if len(ends) != 2:
            raise ValueError("'interval' must be a vector of length 2")
        if lower is None:
            lower = min(ends)
        if upper is None:
            upper = max(ends)
    if lower is None or upper is None or not math.isfinite(lower) or not math.isfinite(upper) or lower >= upper:
        raise ValueError("lower < upper  is not fulfilled")
    if tol is None:
        tol = _EPS**0.2
    grid = [lower + (upper - lower) * i / n for i in range(n + 1)]
    values = f(grid, **kwargs)
    values = [float(item) for item in values]
    roots = [grid[index] for index, value in enumerate(values) if value == 0.0]
    for index in range(n):
        if values[index] * values[index + 1] < 0.0:
            roots.append(
                _uniroot(
                    lambda point: float(f(point, **kwargs)),
                    grid[index],
                    grid[index + 1],
                    tol,
                    maxiter,
                )
            )
    return roots
