"""ODE initial-value and boundary-value solvers from pracma."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Norm, dot, eye
from pracma.elementary import eps, linspace

_MACHINE_EPS = float(np.finfo(float).eps)
_SQRT_EPS = math.sqrt(_MACHINE_EPS)


def _sign(value):
    value = float(value)
    if value > 0.0:
        return 1.0
    if value < 0.0:
        return -1.0
    return 0.0


def _scalar(value, label):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.numeric({label}) is not TRUE")
    array = np.asarray(value)
    if array.dtype == bool or not np.issubdtype(array.dtype, np.number) or array.size != 1:
        raise PracmaError(f"length({label}) == 1 is not TRUE")
    return float(array.reshape(-1)[0])


def _state(y0, column_message=None):
    if isinstance(y0, (bool, np.bool_)):
        raise PracmaError("is.numeric(y0) is not TRUE")
    array = np.asarray(y0)
    if array.dtype == bool or array.dtype == object or not np.issubdtype(array.dtype, np.number):
        raise PracmaError("is.numeric(y0) is not TRUE")
    array = np.array(array, dtype=float, copy=True)
    if array.ndim == 2:
        if array.shape[1] != 1:
            raise PracmaError(column_message or "Argument 'y0' must be a vector or single column matrix.")
        return array.reshape(-1)
    if array.ndim > 2:
        raise PracmaError(column_message or "Argument 'y0' must be a vector or single column matrix.")
    return array.reshape(-1)


def _eval_f(fun, t, y, args):
    state = np.asarray(y, dtype=float).reshape(-1)
    value = fun(t, state, *args) if args else fun(t, state)
    return np.asarray(value, dtype=float).reshape(-1)


def _eval_scalar(fun, t, y, args):
    value = fun(t, y, *args) if args else fun(t, y)
    return float(np.asarray(value, dtype=float).reshape(-1)[0])


def _f_col(fun, t, y, args):
    return _eval_f(fun, t, y, args).reshape(-1, 1)


def _stack(rows):
    return np.vstack([np.asarray(row, dtype=float).reshape(1, -1) for row in rows])


def _seq_by(start, stop, step):
    """R seq(from, to, by) with the 1e-10 step count."""
    start = float(start)
    stop = float(stop)
    step = float(step)
    span = stop - start
    if span == 0.0 and stop == 0.0:
        return np.array([start])
    count = span / step
    if not math.isfinite(count):
        raise PracmaError("invalid '(to - from)/by'")
    largest = max(abs(start), abs(stop))
    if largest != 0.0 and abs(span) / largest < 100.0 * _MACHINE_EPS:
        return np.array([start])
    if count < 0.0:
        raise PracmaError("wrong sign in 'by' argument")
    steps = int(count + 1e-10)
    return start + np.arange(steps + 1, dtype=float) * step


def _nunique(values):
    found = []
    for value in values:
        if not any(value == item or (math.isnan(value) and math.isnan(item)) for item in found):
            found.append(value)
    return len(found)


def _zeroin(f, a, b, maxiter=100, tol=1e-07):
    a = float(a)
    b = float(b)
    mu = 0.5
    info = 0
    if a > b:
        a, b = b, a
    fa = float(f(a))
    fb = float(f(b))
    if _sign(fa) * _sign(fb) > 0.0:
        raise PracmaError("Function must differ in sign at interval endpoints.")
    itype = 1
    if abs(fa) < abs(fb):
        u, fu = a, fa
    else:
        u, fu = b, fb
    d = e = u
    fd = fe = fu
    mba = mu * (b - a)
    niter = 0
    c = u
    while niter < maxiter:
        if itype == 1:
            if (b - a) <= 2.0 * (2.0 * abs(u) * _MACHINE_EPS + tol):
                info = 1
                break
            if abs(fa) <= 1e3 * abs(fb) and abs(fb) <= 1e3 * abs(fa):
                c = u - (a - b) / (fa - fb) * fu
            else:
                c = 0.5 * (a + b)
            d, fd = u, fu
            itype = 5
        elif itype == 2 or itype == 3:
            distinct = _nunique((fa, fb, fd, fe))
            if distinct == 4:
                q11 = (d - e) * fd / (fe - fd)
                q21 = (b - d) * fb / (fd - fb)
                q31 = (a - b) * fa / (fb - fa)
                d21 = (b - d) * fd / (fd - fb)
                d31 = (a - b) * fb / (fb - fa)
                q22 = (d21 - q11) * fb / (fe - fb)
                q32 = (d31 - q21) * fa / (fd - fa)
                d32 = (d31 - q21) * fd / (fd - fa)
                q33 = (d32 - q22) * fa / (fe - fa)
                c = a + q31 + q32 + q33
            if distinct < 4 or _sign(c - a) * _sign(c - b) > 0.0:
                a0 = fa
                a1 = (fb - fa) / (b - a)
                a2 = ((fd - fb) / (d - b) - a1) / (d - a)
                c = a - a0 / a1
                if a2 != 0.0:
                    c = a - a0 / a1
                    for _ in range(itype):
                        pc = a0 + (a1 + a2 * (c - b)) * (c - a)
                        pdc = a1 + a2 * (2.0 * c - a - b)
                        if pdc == 0.0:
                            c = a - a0 / a1
                            break
                        c = c - pc / pdc
            itype = itype + 1
        elif itype == 4:
            c = u - 2.0 * (b - a) / (fb - fa) * fu
            if abs(c - u) > 0.5 * (b - a):
                c = 0.5 * (b + a)
            itype = 5
        elif itype == 5:
            c = 0.5 * (b + a)
            itype = 2

        delta = 2.0 * 0.7 * (2.0 * abs(u) * _MACHINE_EPS + tol)
        if (b - a) <= 2.0 * delta:
            c = (a + b) / 2.0
        else:
            c = max(a + delta, min(b - delta, c))
        fc = float(f(c))
        niter += 1
        if _sign(fc - fa) * _sign(fc - fb) >= 0.0:
            fe = fc
        else:
            e, fe = d, fd
        if _sign(fa) * _sign(fc) < 0.0:
            d, fd = b, fb
            b, fb = c, fc
        elif _sign(fb) * _sign(fc) < 0.0:
            d, fd = a, fa
            a, fa = c, fc
        elif fc == 0.0:
            a = b = c
            fa = fb = fc
            info = 1
            break
        else:
            raise PracmaError("zeroin: zero point could not be bracketed")
        if abs(fa) < abs(fb):
            u, fu = a, fa
        else:
            u, fu = b, fb
        if b - a <= 2.0 * (2.0 * abs(u) * _MACHINE_EPS + tol):
            info = 1
            break
        if itype == 5 and (b - a) <= mba:
            itype = 2
        if itype == 2:
            mba = mu * (b - a)
    return {"bra": (a, b), "ket": (fa, fb), "niter": niter, "info": info}


def _fzero(fun, x, maxiter=500, tol=1e-12):
    guess = np.asarray(x, dtype=float).reshape(-1)
    if guess.size == 0 or guess.size > 2:
        raise PracmaError("Argument 'x' must be a scalar or a vector of length 2.")

    def f(point):
        return float(np.asarray(fun(point), dtype=float).reshape(-1)[0])

    if guess.size == 2:
        a, b = float(guess[0]), float(guess[1])
        if a > b:
            a, b = b, a
        bracket = _zeroin(f, a, b, maxiter=maxiter, tol=tol)
    else:
        a = float(guess[0])
        fa = f(a)
        if fa == 0.0:
            return a
        aa = 1.0 if a == 0.0 else a
        bracket = None
        for b in (0.9 * aa, 1.1 * aa, aa - 1.0, aa + 1.0, 0.5 * aa, 1.5 * aa, -aa, 2.0 * aa, -10.0 * aa, 10.0 * aa):
            fb = f(b)
            if fb == 0.0:
                return b
            if _sign(fa) * _sign(fb) < 0.0:
                bracket = _zeroin(f, a, b, maxiter=maxiter, tol=tol)
                break
        if bracket is None:
            return math.nan
    x1, x2 = bracket["bra"]
    f1, f2 = bracket["ket"]
    x0 = (x1 + x2) / 2.0
    f0 = f(x0)
    if f0 < f1 and f0 < f2:
        return x0
    if f1 <= f2:
        return x1
    return x2


def _jacobian(fun, x0, heps=None):
    if heps is None:
        heps = float(_MACHINE_EPS ** (1.0 / 3.0))
    base = np.asarray(x0, dtype=float).reshape(-1)
    n = base.size
    m = np.asarray(fun(base), dtype=float).reshape(-1).size
    jacob = np.empty((m, n), dtype=float)
    hh = np.zeros(n)
    for i in range(n):
        hh[i] = heps
        forward = np.asarray(fun(base + hh), dtype=float).reshape(-1)
        backward = np.asarray(fun(base - hh), dtype=float).reshape(-1)
        jacob[:, i] = (forward - backward) / (2.0 * heps)
        hh[i] = 0.0
    return jacob


def _inv(matrix):
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return np.full(matrix.shape, np.inf)


def _frobenius(matrix):
    values = np.asarray(matrix, dtype=float)
    return math.sqrt(float(np.sum(values * values)))


def _broyden(fun, x0, J0=None, maxiter=100, tol=None):
    if tol is None:
        tol = _SQRT_EPS
    origin = np.asarray(x0, dtype=float).reshape(-1)
    y0 = np.asarray(fun(origin), dtype=float).reshape(-1)
    n = origin.size
    if y0.size != n:
        raise PracmaError("Function 'F' must be 'square', i.e. from R^n to R^n .")
    if n == 1:
        raise PracmaError("Function 'F' must not be a univariate function.")
    A0 = _jacobian(fun, origin) if J0 is None else np.asarray(J0, dtype=float)
    B0 = _inv(A0)
    if np.any(np.isinf(B0)):
        B0 = np.eye(n)
    x_new = origin.reshape(-1, 1) - B0 @ y0.reshape(-1, 1)
    y_new = np.asarray(fun(x_new.reshape(-1)), dtype=float).reshape(-1)
    k = 1
    while k < maxiter:
        s = x_new - origin.reshape(-1, 1)
        d = (y_new - y0).reshape(-1, 1)
        if _frobenius(s) < tol or _frobenius(y_new.reshape(-1, 1)) < tol:
            break
        step = B0 @ d
        denom = float((s.T @ B0 @ d).reshape(-1)[0])
        B0 = B0 + ((s - step) @ s.T @ B0) / denom
        origin = x_new.reshape(-1).copy()
        y0 = y_new.copy()
        x_new = x_new - B0 @ y_new.reshape(-1, 1)
        y_new = np.asarray(fun(x_new.reshape(-1)), dtype=float).reshape(-1)
        k += 1
    return x_new.reshape(-1)


def _fsolve(fun, x0, maxiter=100, tol=None):
    if tol is None:
        tol = _SQRT_EPS
    origin = np.asarray(x0, dtype=float).reshape(-1)
    if origin.size == 1:
        raise PracmaError("Function 'fsolve' not applicable for univariate root finding.")
    return _broyden(fun, origin, J0=_jacobian(fun, origin), maxiter=maxiter, tol=tol)


def _trisolve(a, b, d, rhs):
    diagonal = np.array(a, dtype=float, copy=True).reshape(-1)
    upper = np.array(b, dtype=float, copy=True).reshape(-1)
    lower = np.array(d, dtype=float, copy=True).reshape(-1)
    x = np.array(rhs, dtype=float, copy=True).reshape(-1)
    n = diagonal.size
    if n < 3:
        raise PracmaError("Argument 'n' must be greater or equal 3.")
    if upper.size != n - 1 or lower.size != n - 1:
        raise PracmaError("Vectors 'b' and 'd' must be of a length of length(a)-1.")
    if x.size != n:
        raise PracmaError("Vector 'rhs' must be of the same length as 'a'.")
    upper = np.concatenate([upper, [0.0]])
    for i in range(n - 1):
        if lower[i] != 0.0:
            pivot = diagonal[i] / lower[i]
            si = 1.0 / math.sqrt(1.0 + pivot * pivot)
            co = pivot * si
            diagonal[i] = diagonal[i] * co + lower[i] * si
            hold = upper[i]
            upper[i] = hold * co + diagonal[i + 1] * si
            diagonal[i + 1] = -hold * si + diagonal[i + 1] * co
            lower[i] = upper[i + 1] * si
            upper[i + 1] = upper[i + 1] * co
            hold = x[i]
            x[i] = hold * co + x[i + 1] * si
            x[i + 1] = -hold * si + x[i + 1] * co
    if np.any(diagonal == 0.0):
        raise PracmaError("Triangular matrix is singular -- system not solvable.")
    x[n - 1] = x[n - 1] / diagonal[n - 1]
    x[n - 2] = (x[n - 2] - upper[n - 2] * x[n - 1]) / diagonal[n - 2]
    for i in range(n - 3, -1, -1):
        x[i] = (x[i] - upper[i] * x[i + 1] - lower[i] * x[i + 2]) / diagonal[i]
    return x


def _match_arg(name, choices):
    if name in choices:
        return name
    hits = [choice for choice in choices if choice.startswith(name)]
    if len(hits) == 1:
        return hits[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise PracmaError(f"'arg' should be one of {quoted}")


def _rkf_control(control):
    cntrl = {"hmin": 0.001, "hmax": 0.250, "jmax": 200}
    if not control:
        return cntrl
    matched = [_match_arg(str(name), list(cntrl)) for name in control]
    for key, name in zip(matched, control):
        cntrl[key] = control[name]
    return cntrl


def _midp(fun, x0, xfinal, y0, nsteps, args):
    h = (xfinal - x0) / nsteps
    x = float(x0)
    y1 = np.asarray(y0, dtype=float).reshape(-1).copy()
    y2 = y1 + h * _eval_f(fun, x, y1, args)
    for _ in range(nsteps - 1):
        x = x + h
        yy = y1 + 2.0 * h * _eval_f(fun, x, y2, args)
        y1 = y2
        y2 = yy
    return 0.5 * (y1 + y2 + h * _eval_f(fun, x, yy, args))


def _richardson(fun, t0, tfinal, y0, tol, args, kmax=25):
    state = np.asarray(y0, dtype=float).reshape(-1)
    n = state.size
    table = np.full((kmax, n), np.nan)
    nsteps = 2
    table[0] = _midp(fun, t0, tfinal, state, nsteps, args)
    previous = table[0].copy()
    for k in range(2, kmax + 1):
        nsteps *= 2
        table[k - 1] = _midp(fun, t0, tfinal, state, nsteps, args)
        for j in range(k - 2, -1, -1):
            cc = 4.0 ** (k - j - 1)
            table[j] = (cc * table[j + 1] - table[j]) / (cc - 1.0)
        difference = table[0] - previous
        product = dot(difference, difference)
        err = math.sqrt(float(np.reshape(product, -1)[0]) / n)
        if err < tol:
            break
        previous = table[0].copy()
    return table[0]


def bulirsch_stoer(f, t, y0, tol=1e-08, *args):
    if not callable(f):
        raise PracmaError("is.function(f) is not TRUE")
    grid = np.asarray(t, dtype=float).reshape(-1)
    state = np.asarray(y0, dtype=float).reshape(-1)
    if grid.size < 2:
        raise PracmaError("Argument 't' must be a vector of length at least 2.")
    image = _eval_f(f, grid[0], state, args)
    if state.size != image.size:
        raise PracmaError("Argument 'y0' and 'f(..)' must be of the same length.")
    step_tol = tol / (grid.size - 1)
    values = np.zeros((grid.size, image.size))
    values[0] = state
    for i in range(1, grid.size):
        values[i] = _richardson(f, grid[i - 1], grid[i], values[i - 1], step_tol, args)
    return values


def midpoint(f, t0, tfinal, y0, tol=1e-08, kmax=101, *args):
    del tol
    if not callable(f):
        raise PracmaError("is.function(f) is not TRUE")
    t0 = _scalar(t0, "t0")
    tfinal = _scalar(tfinal, "tfinal")
    message = "midpoint: Argument 'y0' must be row or column vector."
    state = _state(y0, message)
    n = int(math.trunc(float(kmax)))
    y_length = state.size
    image = _eval_f(f, t0, state, args)
    if image.size != y_length:
        raise PracmaError("midpoint: Function f must have the same length as 'y0'.")
    ts = np.asarray(linspace(t0, tfinal, n), dtype=float).reshape(-1)
    dt = (tfinal - t0) / (n - 1)
    if y_length == 1:
        y = float(state[0])
        yout = np.full(n, np.nan)
        yout[0] = y
        for i in range(1, n):
            t_left = float(ts[i - 1])
            tw = t_left + 0.5 * dt
            guess = y + 0.5 * dt * _eval_scalar(f, t_left, y, args)

            def residual(w, y=y, tw=tw):
                return (float(w) - y) - 0.5 * dt * _eval_scalar(f, tw, float(w), args)

            root = _fzero(residual, guess)
            y = 2.0 * root - yout[i - 1]
            yout[i] = y
        return {"t": ts, "y": yout}
    y = state.copy()
    yout = np.full((n, y_length), np.nan)
    yout[0] = y
    for i in range(1, n):
        t_left = float(ts[i - 1])
        tw = t_left + 0.5 * dt
        guess = y + 0.5 * dt * _eval_f(f, t_left, y, args)

        def residual(w, y=y.copy(), tw=tw):
            point = np.asarray(w, dtype=float).reshape(-1)
            return (point - y) - 0.5 * dt * _eval_f(f, tw, point, args)

        root = _fsolve(residual, guess)
        y = 2.0 * root - yout[i - 1]
        yout[i] = y
    return {"t": ts, "y": yout}


def ode23s(f, t0, tfinal, y0, jac=None, *args, rtol=1e-03, atol=1e-06, hmax=0.0):
    t0 = _scalar(t0, "t0")
    tfinal = _scalar(tfinal, "tfinal")
    message = "Argument 'y0' must be a vector or single column matrix."
    y = _state(y0, message)
    image = _eval_f(f, t0, y, args)
    if image.size != y.size:
        raise PracmaError("Argument 'f' does not describe a system of equations.")
    n = y.size
    m = image.size
    if jac is None:
        def jac_fun(t, x):
            point = np.asarray(x, dtype=float).reshape(-1)
            jacob = np.empty((m, n))
            hh = np.zeros(n)
            heps = 5e-06
            for i in range(n):
                hh[i] = heps
                jacob[:, i] = (
                    _eval_f(f, t, point + hh, args) - _eval_f(f, t, point - hh, args)
                ) / (2.0 * heps)
                hh[i] = 0.0
            return jacob
    else:
        def jac_fun(t, x):
            point = np.asarray(x, dtype=float).reshape(-1)
            return np.asarray(jac(t, point), dtype=float)

    dcoef = 1.0 / (2.0 + math.sqrt(2.0))
    cc = 0.5
    e32 = 6.0 + math.sqrt(2.0)
    t = t0
    tdir = _sign(tfinal - t)
    h = tdir * 0.01 * (tfinal - t)
    if hmax == 0.0:
        hmax = 0.1 * abs(tfinal - t)
    hmin = min(16.0 * eps(tfinal - t), h)
    times = [t]
    rows = [y.copy()]
    while abs(t) < abs(tfinal) and hmin < abs(h):
        if abs(t - tfinal) < abs(h):
            h = tfinal - t
        J = jac_fun(t, y)
        T = (_eval_f(f, t + 0.01 * h, y, args) - _eval_f(f, t, y, args)) / (0.01 * h)
        W = eye(n) - h * dcoef * J
        F1 = _eval_f(f, t, y, args)
        k1 = np.linalg.solve(W, F1 + h * dcoef * T)
        F2 = _eval_f(f, t + cc * h, y + cc * h * k1, args)
        k2 = np.linalg.solve(W, F2 - k1) + k1
        ynew = y + h * k2
        F3 = _eval_f(f, t + h, ynew, args)
        k3 = np.linalg.solve(W, F3 - e32 * (k2 - F2) - 2.0 * (k1 - F1) + h * dcoef * T)
        err = h / 6.0 * Norm(k1 - 2.0 * k2 + k3)
        tau = max(rtol * max(Norm(y), Norm(ynew)), atol)
        if err <= tau:
            t = t + h
            times.append(t)
            y = ynew
            rows.append(y.copy())
            if err == 0.0:
                err = eps() / 2.0
        h = tdir * min(hmax, abs(h) * 0.8 * (tau / err) ** (1.0 / 3.0))
        if abs(h) > hmax:
            h = _sign(h) * hmax
    return {"t": np.asarray(times, dtype=float), "y": _stack(rows)}


_DP = np.array(
    [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.0 / 5.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [3.0 / 40.0, 9.0 / 40.0, 0.0, 0.0, 0.0, 0.0],
        [44.0 / 45.0, -56.0 / 15.0, 32.0 / 9.0, 0.0, 0.0, 0.0],
        [19372.0 / 6561.0, -25360.0 / 2187.0, 64448.0 / 6561.0, -212.0 / 729.0, 0.0, 0.0],
        [9017.0 / 3168.0, -355.0 / 33.0, 46732.0 / 5247.0, 49.0 / 176.0, -5103.0 / 18656.0, 0.0],
        [35.0 / 384.0, 0.0, 500.0 / 1113.0, 125.0 / 192.0, -2187.0 / 6784.0, 11.0 / 84.0],
    ],
    dtype=float,
)
_B4 = np.array(
    [5179.0 / 57600.0, 0.0, 7571.0 / 16695.0, 393.0 / 640.0, -92097.0 / 339200.0, 187.0 / 2100.0, 1.0 / 40.0],
    dtype=float,
)
_B5 = np.array(
    [35.0 / 384.0, 0.0, 500.0 / 1113.0, 125.0 / 192.0, -2187.0 / 6784.0, 11.0 / 84.0, 0.0],
    dtype=float,
)
_DP_C = _DP.sum(axis=1)


def ode45(f, t0, tfinal, y0, *args, atol=1e-6, hmax=0.0):
    t0 = _scalar(t0, "t0")
    tfinal = _scalar(tfinal, "tfinal")
    message = "Argument 'y0' must be a vector or single column matrix."
    x = _state(y0, message).reshape(-1, 1)
    if hmax == 0.0:
        hmax = (tfinal - t0) / 2.5
    t = t0
    hmin = (tfinal - t) / 1e20
    h = (tfinal - t) / 100.0
    nstates = x.shape[0]
    capacity = math.floor(1e3 * (tfinal - t0))
    times = [t]
    rows = [x.reshape(-1).copy()]
    accepted = 1
    kk = np.zeros((nstates, 7))
    kk[:, 0:1] = _f_col(f, t, x, args)
    while t < tfinal and h >= hmin:
        if t + h > tfinal:
            h = tfinal - t
        for j in range(6):
            increment = kk[:, 0 : j + 1] @ _DP[j + 1, 0 : j + 1].reshape(-1, 1)
            kk[:, j + 1 : j + 2] = _f_col(f, t + _DP_C[j + 1] * h, x + h * increment, args)
        x5 = x + h * (kk @ _B5).reshape(-1, 1)
        gamma1 = x5 - (x + h * (kk @ _B4).reshape(-1, 1))
        delta = Norm(gamma1, np.inf)
        tau = atol * max(Norm(x, np.inf), 1.0)
        if delta < tau:
            t = t + h
            x = x5
            accepted += 1
            if accepted > capacity:
                raise PracmaError("subscript out of bounds")
            times.append(t)
            rows.append(x.reshape(-1).copy())
            kk[:, 0:1] = kk[:, 6:7]
        if delta == 0.0:
            delta = 1e-16
        h = min(hmax, 0.8 * h * (tau / delta) ** (1.0 / 6.0))
    y = _stack(rows)
    tout = np.asarray(times, dtype=float)
    if accepted < capacity:
        if nstates == 1:
            y = y[:, 0]
    else:
        tout = tout.reshape(-1, 1)
    return {"t": tout, "y": y}


_ALPHA78 = np.array(
    [2.0 / 27.0, 1.0 / 9.0, 1.0 / 6.0, 5.0 / 12.0, 0.5, 5.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0, 1.0 / 3.0, 1.0, 0.0, 1.0],
    dtype=float,
)
_BETA78 = np.array(
    [
        [2.0 / 27.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.0 / 36.0, 1.0 / 12.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.0 / 24.0, 0.0, 1.0 / 8.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [5.0 / 12.0, 0.0, -25.0 / 16.0, 25.0 / 16.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.05, 0.0, 0.0, 0.25, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [-25.0 / 108.0, 0.0, 0.0, 125.0 / 108.0, -65.0 / 27.0, 125.0 / 54.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [31.0 / 300.0, 0.0, 0.0, 0.0, 61.0 / 225.0, -2.0 / 9.0, 13.0 / 900.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0, -53.0 / 6.0, 704.0 / 45.0, -107.0 / 9.0, 67.0 / 90.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [-91.0 / 108.0, 0.0, 0.0, 23.0 / 108.0, -976.0 / 135.0, 311.0 / 54.0, -19.0 / 60.0, 17.0 / 6.0, -1.0 / 12.0, 0.0, 0.0, 0.0, 0.0],
        [2383.0 / 4100.0, 0.0, 0.0, -341.0 / 164.0, 4496.0 / 1025.0, -301.0 / 82.0, 2133.0 / 4100.0, 45.0 / 82.0, 45.0 / 164.0, 18.0 / 41.0, 0.0, 0.0, 0.0],
        [3.0 / 205.0, 0.0, 0.0, 0.0, 0.0, -6.0 / 41.0, -3.0 / 205.0, -3.0 / 41.0, 3.0 / 41.0, 6.0 / 41.0, 0.0, 0.0, 0.0],
        [-1777.0 / 4100.0, 0.0, 0.0, -341.0 / 164.0, 4496.0 / 1025.0, -289.0 / 82.0, 2193.0 / 4100.0, 51.0 / 82.0, 33.0 / 164.0, 12.0 / 41.0, 0.0, 1.0, 0.0],
    ],
    dtype=float,
).T
_CHI78 = np.array(
    [0.0, 0.0, 0.0, 0.0, 0.0, 34.0 / 105.0, 9.0 / 35.0, 9.0 / 35.0, 9.0 / 280.0, 9.0 / 280.0, 0.0, 41.0 / 840.0, 41.0 / 840.0],
    dtype=float,
).reshape(-1, 1)
_PSI78 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, -1.0, -1.0], dtype=float).reshape(-1, 1)


def ode78(f, t0, tfinal, y0, *args, atol=1e-6, hmax=0.0):
    t0 = _scalar(t0, "t0")
    tfinal = _scalar(tfinal, "tfinal")
    message = "Argument 'y0' must be a vector or single column matrix."
    x = _state(y0, message).reshape(-1, 1)
    if hmax == 0.0:
        hmax = (tfinal - t0) / 2.5
    t = t0
    hmin = (tfinal - t) / 1e20
    h = (tfinal - t) / 50.0
    nstates = x.shape[0]
    times = [t]
    rows = [x.reshape(-1).copy()]
    ff = np.zeros((nstates, 13))
    while t < tfinal and h >= hmin:
        if t + h > tfinal:
            h = tfinal - t
        ff[:, 0:1] = _f_col(f, t, x, args)
        for j in range(12):
            increment = ff @ _BETA78[:, j : j + 1]
            ff[:, j + 1 : j + 2] = _f_col(f, t + _ALPHA78[j] * h, x + h * increment, args)
        gamma1 = h * (41.0 / 840.0) * (ff @ _PSI78)
        delta = Norm(gamma1, np.inf)
        tau = atol * max(Norm(x, np.inf), 1.0)
        if delta <= tau:
            t = t + h
            x = x + h * (ff @ _CHI78)
            times.append(t)
            rows.append(x.reshape(-1).copy())
        if delta == 0.0:
            delta = 1e-16
        h = min(hmax, 0.8 * h * (tau / delta) ** (1.0 / 8.0))
    return {"t": np.asarray(times, dtype=float), "y": _stack(rows)}


def ode23(f, t0, tfinal, y0, *args, rtol=1e-3, atol=1e-6):
    t0 = _scalar(t0, "t0")
    tfinal = _scalar(tfinal, "tfinal")
    message = "Argument 'y0' must be a vector or single column matrix."
    y = _state(y0, message)
    image = _eval_f(f, t0, y, args)
    if image.size != y.size:
        raise PracmaError("Argument 'f' does not describe a system of equations.")
    realmin = 1e-100
    tdir = _sign(tfinal - t0)
    threshold = atol / rtol
    hmax = abs(0.1 * (tfinal - t0))
    t = t0
    times = [t]
    rows = [y.copy()]
    s1 = _eval_f(f, t, y, args)
    level = max(float(np.max(np.abs(y))), threshold)
    rate = float(np.max(np.abs(s1 / level))) + realmin
    h = tdir * 0.8 * rtol ** (1.0 / 3.0) / rate
    while t != tfinal:
        hmin = 16.0 * _MACHINE_EPS * abs(t)
        if abs(h) > hmax:
            h = tdir * hmax
        elif abs(h) < hmin:
            h = tdir * hmin
        if 1.1 * abs(h) >= abs(tfinal - t):
            h = tfinal - t
        s2 = _eval_f(f, t + h / 2.0, y + (h / 2.0) * s1, args)
        s3 = _eval_f(f, t + 3.0 * h / 4.0, y + (3.0 * h / 4.0) * s2, args)
        tnew = t + h
        ynew = y + h * (2.0 * s1 + 3.0 * s2 + 4.0 * s3) / 9.0
        s4 = _eval_f(f, tnew, ynew, args)
        error = h * (-5.0 * s1 + 6.0 * s2 + 8.0 * s3 - 9.0 * s4) / 72.0
        level = max(float(np.max(np.abs(y))), float(np.max(np.abs(ynew))), threshold)
        err = float(np.max(np.abs(error / level))) + realmin
        if err <= rtol:
            t = tnew
            y = ynew
            times.append(t)
            rows.append(y.copy())
            s1 = s4
        h = h * min(5.0, 0.8 * (rtol / err) ** (1.0 / 3.0))
        if abs(h) <= hmin:
            t = tfinal
    return {"t": np.asarray(times, dtype=float), "y": _stack(rows)}


def rkf54(f, a, b, y0, tol=_SQRT_EPS, control=None, *args):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    if tol < _MACHINE_EPS:
        tol = _MACHINE_EPS
    cntrl = _rkf_control({} if control is None else control)
    hmin = float(cntrl["hmin"])
    hmax = float(cntrl["hmax"])
    jmax = cntrl["jmax"]
    y0 = float(np.asarray(y0, dtype=float).reshape(-1)[0])
    a2, b2 = 1.0 / 4.0, 1.0 / 4.0
    a3, b3, c3 = 3.0 / 8.0, 3.0 / 32.0, 9.0 / 32.0
    a4, b4, c4, d4 = 12.0 / 13.0, 1932.0 / 2197.0, -7200.0 / 2197.0, 7296.0 / 2197.0
    a5, b5, c5, d5, e5 = 1.0, 439.0 / 216.0, -8.0, 3680.0 / 513.0, -845.0 / 4104.0
    a6, b6, c6, d6, e6, f6 = 1.0 / 2.0, -8.0 / 27.0, 2.0, -3544.0 / 2565.0, 1859.0 / 4104.0, -11.0 / 40.0
    r1, r3, r4, r5, r6 = 1.0 / 360.0, -128.0 / 4275.0, -2197.0 / 75240.0, 1.0 / 50.0, 2.0 / 55.0
    n1, n3, n4, n5 = 25.0 / 216.0, 1408.0 / 2565.0, 2197.0 / 4104.0, -1.0 / 5.0
    j = 1
    T = [a]
    Y = [y0]
    h = 0.8 * hmin + 0.2 * hmax
    br = b - tol * abs(b)
    while T[j - 1] < b:
        if T[j - 1] + h > br:
            h = b - T[j - 1]
        tj = T[j - 1]
        yj = Y[j - 1]
        k1 = h * _eval_scalar(f, tj, yj, args)
        k2 = h * _eval_scalar(f, tj + a2 * h, yj + b2 * k1, args)
        k3 = h * _eval_scalar(f, tj + a3 * h, yj + b3 * k1 + c3 * k2, args)
        k4 = h * _eval_scalar(f, tj + a4 * h, yj + b4 * k1 + c4 * k2 + d4 * k3, args)
        k5 = h * _eval_scalar(f, tj + a5 * h, yj + b5 * k1 + c5 * k2 + d5 * k3 + e5 * k4, args)
        k6 = h * _eval_scalar(f, tj + a6 * h, yj + b6 * k1 + c6 * k2 + d6 * k3 + e6 * k4 + f6 * k5, args)
        err = abs(r1 * k1 + r3 * k3 + r4 * k4 + r5 * k5 + r6 * k6)
        ynew = yj + n1 * k1 + n3 * k3 + n4 * k4 + n5 * k5
        if err < tol or h < 2.0 * hmin:
            Y.append(ynew)
            if tj + h > br:
                T.append(b)
            else:
                T.append(tj + h)
            j += 1
        if err == 0.0:
            s = 0.0
        else:
            s = (tol * h / (2.0 * err)) ** 0.25
        if s < 0.1:
            s = 0.1
        if s > 4.0:
            s = 4.0
        h = s * h
        if h > hmax:
            h = hmax
        if h < hmin:
            h = hmin
        if j >= jmax:
            break
    return {"x": np.asarray(T, dtype=float), "y": np.asarray(Y, dtype=float)}


def rk4(f, a, b, y0, n):
    a = float(a)
    b = float(b)
    y0 = float(np.asarray(y0, dtype=float).reshape(-1)[0])
    n_value = float(n)
    steps = int(math.trunc(n_value))
    h = (b - a) / n_value
    grid = _seq_by(a + h, b, h)
    y = np.zeros(steps)
    k1 = h * _eval_scalar(f, a, y0, ())
    k2 = h * _eval_scalar(f, a + h / 2.0, y0 + k1 / 2.0, ())
    k3 = h * _eval_scalar(f, a + h / 2.0, y0 + k2 / 2.0, ())
    k4 = h * _eval_scalar(f, a + h, y0 + k3, ())
    y[0] = y0 + k1 / 6.0 + k2 / 3.0 + k3 / 3.0 + k4 / 6.0
    for i in range(steps - 1):
        node = float(grid[i])
        k1 = h * _eval_scalar(f, node, y[i], ())
        k2 = h * _eval_scalar(f, node + h / 2.0, y[i] + k1 / 2.0, ())
        k3 = h * _eval_scalar(f, node + h / 2.0, y[i] + k2 / 2.0, ())
        k4 = h * _eval_scalar(f, node + h, y[i] + k3, ())
        y[i + 1] = y[i] + k1 / 6.0 + k2 / 3.0 + k3 / 3.0 + k4 / 6.0
    return {"x": np.concatenate([[a], grid]), "y": np.concatenate([[y0], y])}


def rk4sys(f, a, b, y0, n):
    a = float(a)
    b = float(b)
    state = np.asarray(y0, dtype=float).reshape(-1)
    m = state.size
    n_value = float(n)
    steps = int(math.trunc(n_value))
    h = (b - a) / n_value
    grid = _seq_by(a + h, b, h)
    y = np.zeros((steps, m))
    k1 = h * _eval_f(f, a, state, ())
    k2 = h * _eval_f(f, a + h / 2.0, state + k1 / 2.0, ())
    k3 = h * _eval_f(f, a + h / 2.0, state + k2 / 2.0, ())
    k4 = h * _eval_f(f, a + h, state + k3, ())
    y[0] = state + k1 / 6.0 + k2 / 3.0 + k3 / 3.0 + k4 / 6.0
    for i in range(steps - 1):
        node = float(grid[i])
        k1 = h * _eval_f(f, node, y[i], ())
        k2 = h * _eval_f(f, node + h / 2.0, y[i] + k1 / 2.0, ())
        k3 = h * _eval_f(f, node + h / 2.0, y[i] + k2 / 2.0, ())
        k4 = h * _eval_f(f, node + h, y[i] + k3, ())
        y[i + 1] = y[i] + k1 / 6.0 + k2 / 3.0 + k3 / 3.0 + k4 / 6.0
    return {"x": np.concatenate([[a], grid]), "y": np.vstack([state.reshape(1, -1), y])}


def _coeff_fun(value):
    if callable(value):
        return value
    number = float(np.asarray(value, dtype=float).reshape(-1)[0])

    def wrapped(xs):
        return np.full(np.asarray(xs, dtype=float).shape, number, dtype=float)

    return wrapped


def bvp(f, g, h, x, y, n=50):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size != 2 or y.size != 2:
        raise PracmaError("Arguments 'x' and 'y' must have length 2.")
    n_value = float(np.asarray(n, dtype=float).reshape(-1)[0])
    if n_value != math.floor(n_value) or n_value < 2:
        raise PracmaError("Argument 'n' must be an integer greater or equal 2.")
    n_int = int(n_value)
    ffun = _coeff_fun(f)
    gfun = _coeff_fun(g)
    hfun = _coeff_fun(h)
    xa, xb = float(x[0]), float(x[1])
    ya, yb = float(y[0]), float(y[1])
    xs = np.asarray(linspace(xa, xb, n_int + 2), dtype=float).reshape(-1)[1:-1]
    dt = (xb - xa) / (n_int + 1)
    diagonal = -2.0 - dt**2 * np.asarray(gfun(xs), dtype=float).reshape(-1)
    upper = 1.0 - dt / 2.0 * np.asarray(ffun(xs[:-1]), dtype=float).reshape(-1)
    lower = 1.0 + dt / 2.0 * np.asarray(ffun(xs[1:]), dtype=float).reshape(-1)
    rhs = dt**2 * np.asarray(hfun(xs), dtype=float).reshape(-1)
    f_left = float(np.asarray(ffun(xs[0]), dtype=float).reshape(-1)[0])
    f_right = float(np.asarray(ffun(xs[-1]), dtype=float).reshape(-1)[0])
    rhs = np.array(rhs, dtype=float, copy=True)
    rhs[0] = rhs[0] - ya * (1.0 + (dt / 2.0) * f_left)
    rhs[-1] = rhs[-1] - yb * (1.0 - (dt / 2.0) * f_right)
    ys = _trisolve(diagonal, upper, lower, rhs)
    return {
        "xs": np.concatenate([[xa], xs, [xb]]),
        "ys": np.concatenate([[ya], ys, [yb]]),
    }


def cranknic(f, t0, t1, y0, *args, N=100):
    t0 = _scalar(t0, "t0")
    t1 = _scalar(t1, "t1")
    message = "Argument 'y0' must be a row or column vector."
    state = _state(y0, message)
    steps = int(N)
    n = state.size
    image = _eval_f(f, t0, state, args)
    if image.size != n:
        raise PracmaError("Function f must return a vector the same length as 'y0'.")
    h = (t1 - t0) / (steps - 1)
    ts = np.asarray(linspace(t0, t1, steps), dtype=float).reshape(-1)
    if n == 1:
        y = float(state[0])
        yout = np.full(steps, np.nan)
        yout[0] = y
        for i in range(1, steps):
            t = float(ts[i])

            def residual(w, y=y, t=t):
                return (float(w) - y) - 0.5 * h * (
                    _eval_scalar(f, t, float(w), args) + _eval_scalar(f, t, y, args)
                )

            y = _fzero(residual, y)
            yout[i] = y
        return {"t": ts, "y": yout}
    y = state.copy()
    yout = np.full((steps, n), np.nan)
    yout[0] = y
    for i in range(1, steps):
        t = float(ts[i])

        def residual(w, y=y.copy(), t=t):
            point = np.asarray(w, dtype=float).reshape(-1)
            return (point - y) - 0.5 * h * (_eval_f(f, t, point, args) + _eval_f(f, t, y, args))

        y = _fsolve(residual, y)
        yout[i] = y
    return {"t": ts, "y": yout}


def newmark(f, t0, t1, y0, *args, N=100, zeta=0.25, theta=0.5):
    t0 = _scalar(t0, "t0")
    t1 = _scalar(t1, "t1")
    state = np.asarray(y0, dtype=float).reshape(-1)
    if state.size != 2:
        raise PracmaError("Argument 'y0' must be a numeric vector of length 2.")
    steps = math.floor(float(N))
    if steps < 2:
        raise PracmaError("Argument 'N' must be an integer greater than 1.")
    steps = int(steps)
    y = state.copy()
    yout = np.full((steps, 2), np.nan)
    yout[0] = y
    h = (t1 - t0) / (steps - 1)
    ts = np.asarray(linspace(t0, t1, steps), dtype=float).reshape(-1)
    f1 = _eval_scalar(f, float(ts[0]), y, args)
    for i in range(1, steps):
        t = float(ts[i])

        def residual(w, t=t, y=y.copy(), f1=f1):
            point = np.asarray(w, dtype=float).reshape(-1)
            f2 = _eval_scalar(f, t, point, args)
            z1 = point[0] - y[0] - h * y[1] - h**2 * (zeta * f2 + (0.5 - zeta) * f1)
            z2 = point[1] - y[1] - h * ((1.0 - theta) * f1 + theta * f2)
            return np.array([z1, z2], dtype=float)

        y = _fsolve(residual, y)
        f1 = _eval_scalar(f, t, y, args)
        yout[i] = y
    return {"t": ts, "y": yout}


def abm3pc(f, a, b, y0, n=50, *args):
    a = float(np.asarray(a, dtype=float).reshape(-1)[0])
    b = float(np.asarray(b, dtype=float).reshape(-1)[0])
    y0 = float(np.asarray(y0, dtype=float).reshape(-1)[0])
    n_value = np.asarray(n, dtype=float).reshape(-1)
    if n_value.size != 1 or float(n_value[0]) < 5:
        raise PracmaError("Argument 'n' must be an integer greater or equal to 5.")
    steps = int(math.floor(float(n_value[0])))
    h = (b - a) / steps
    k = h / 12.0
    x = _seq_by(a, b, h)
    z = np.zeros(steps + 1)
    y = np.zeros(steps + 1)
    errorest = np.zeros(steps + 1)
    z[0] = _eval_scalar(f, a, y0, args)
    y[0] = y0
    k1 = h * z[0]
    k2 = h * _eval_scalar(f, a + h / 2.0, y0 + k1 / 2.0, args)
    k3 = h * _eval_scalar(f, a + 0.75 * h, y0 + 0.75 * k2, args)
    y[1] = y0 + (2.0 * k1 + 3.0 * k2 + 4.0 * k3) / 9.0
    z[1] = _eval_scalar(f, x[1], y[1], args)
    k1 = h * z[1]
    k2 = h * _eval_scalar(f, x[1] + h / 2.0, y[1] + k1 / 2.0, args)
    k3 = h * _eval_scalar(f, x[1] + 0.75 * h, y[1] + 0.75 * k2, args)
    y[2] = y[1] + (2.0 * k1 + 3.0 * k2 + 4.0 * k3) / 9.0
    # The installed source samples the second node here, not the value just stored.
    z[2] = _eval_scalar(f, x[1], y[1], args)
    for i in range(3, steps + 1):
        predicted = y[i - 1] + k * (23.0 * z[i - 1] - 16.0 * z[i - 2] + 5.0 * z[i - 3])
        predicted_slope = _eval_scalar(f, x[i], predicted, args)
        y[i] = y[i - 1] + k * (5.0 * predicted_slope + 8.0 * z[i - 1] - z[i - 2])
        z[i] = _eval_scalar(f, x[i], y[i], args)
        errorest[i] = -0.1 * (y[i] - predicted)
    return {"x": x, "y": y, "est.error": np.sqrt(np.abs(errorest))}


def euler_heun(f, a, b, y0, n=100, improved=True, *args):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    y0 = float(np.asarray(y0, dtype=float).reshape(-1)[0])
    probe = f(a, y0, *args) if args else f(a, y0)
    if np.asarray(probe, dtype=float).reshape(-1).size != 1:
        raise PracmaError("Argument function 'f' must be an univariate function.")
    n_value = float(n)
    steps = int(math.trunc(n_value))
    h = (b - a) / n_value
    t = np.asarray(linspace(a, b, steps + 1), dtype=float).reshape(-1)
    y = np.zeros(steps + 1)
    y[0] = y0
    for i in range(steps):
        y[i + 1] = y[i] + h * _eval_scalar(f, t[i], y[i], args)
        if improved:
            y[i + 1] = y[i] + h * (
                _eval_scalar(f, t[i], y[i], args) + _eval_scalar(f, t[i + 1], y[i + 1], args)
            ) / 2.0
    return {"t": t, "y": y}


def shooting(f, t0, tfinal, y0, h, a, b, itermax=20, tol=1e-6, hmax=0):
    t0 = _scalar(t0, "t0")
    tfinal = _scalar(tfinal, "tfinal")
    y0 = float(np.asarray(y0, dtype=float).reshape(-1)[0])
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    limit = int(math.trunc(float(itermax)))
    dy = np.zeros(limit)
    dy[0] = a
    dy[1] = b
    residual = np.zeros(limit)
    test = 1.0
    i = 1
    sol = None

    def wrapped(t, y):
        state = np.asarray(y, dtype=float).reshape(-1)
        acceleration = f(t, float(state[0]), float(state[1]))
        return np.array([state[1], float(np.asarray(acceleration, dtype=float).reshape(-1)[0])])

    while test > tol and i <= limit:
        if i > 2:
            dy[i - 1] = dy[i - 2] - (dy[i - 2] - dy[i - 3]) * residual[i - 2] / (
                residual[i - 2] - residual[i - 3]
            )
        sol = ode45(wrapped, t0, tfinal, np.array([y0, dy[i - 1]]), atol=tol, hmax=hmax)
        end = sol["y"][-1]
        residual[i - 1] = float(h(float(end[0]), float(end[1])))
        test = abs(residual[i - 1])
        i += 1
    return {"t": sol["t"], "y": sol["y"]}
