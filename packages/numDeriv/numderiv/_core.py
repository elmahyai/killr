"""Richardson, complex-step, and simple derivatives from numDeriv 2016.8-1.1."""

import numpy as np

_EPS = float(np.finfo(float).eps)
_ZERO_TOL = float(np.sqrt(_EPS / 7e-7))

_GRAD_RICHARDSON = {
    "eps": 1e-4,
    "d": 0.0001,
    "zero.tol": _ZERO_TOL,
    "r": 4,
    "v": 2,
    "show.details": False,
}
_SIMPLE = {"eps": 1e-4}
_HESS_RICHARDSON = {
    "eps": 1e-4,
    "d": 0.1,
    "zero.tol": _ZERO_TOL,
    "r": 4,
    "v": 2,
    "show.details": False,
}
_GEND_RICHARDSON = {
    "eps": 1e-4,
    "d": 0.0001,
    "zero.tol": _ZERO_TOL,
    "r": 4,
    "v": 2,
}


class Darray(dict):
    """The list genD returns, with class Darray."""


def _stop(message):
    raise ValueError(message)


def _fill(defaults, overrides):
    args = dict(defaults)
    if overrides:
        for key, value in dict(overrides).items():
            args[key] = value
    return args


def _x(x):
    return np.asarray(x, dtype=float).reshape(-1)


def _real(value):
    array = np.asarray(value)
    if array.dtype == object:
        array = np.asarray(array.tolist())
    return np.asarray(array, dtype=float).reshape(-1)


def _scalar(value):
    flat = np.asarray(value, dtype=float).reshape(-1)
    return float(flat[0])


def _complex(value):
    return np.asarray(value, dtype=np.complex128).reshape(-1)


def _whole(value):
    number = float(value)
    whole = int(number)
    if whole != number:
        whole = int(np.floor(number)) if number >= 0 else int(np.ceil(number))
    return whole


def _side(side, n):
    if side is None:
        return np.full(n, np.nan)
    values = np.asarray(side, dtype=float).reshape(-1)
    if values.size != n:
        _stop("Non-NULL argument 'side' should have the same length as x")
    kept = values[~np.isnan(values)]
    if kept.size and np.any(np.abs(kept) != 1):
        _stop("Non-NULL argument 'side' should have values NA, +1, or -1.")
    return values


def _initial_h(x, d, eps, zero_tol):
    return np.abs(np.asarray(d, dtype=float) * x) + np.asarray(eps, dtype=float) * (
        np.abs(x) < np.asarray(zero_tol, dtype=float)
    )


def _one_sided(h, side):
    plus = (side == 1) & ~np.isnan(side)
    minus = (side == -1) & ~np.isnan(side)
    ph = np.array(h, dtype=float, copy=True)
    mh = np.array(h, dtype=float, copy=True)
    ph[plus] = 2 * ph[plus]
    ph[minus] = 0
    mh[minus] = 2 * mh[minus]
    mh[plus] = 0
    return ph, mh


def _unit(n, index):
    step = np.zeros(n)
    step[index] = 1.0
    return step


def _simple_eps(eps, side):
    base = np.atleast_1d(np.asarray(eps, dtype=float))
    return np.tile(base, side.size) * side


def grad(func, x, method="Richardson", side=None, method_args=None, **kwargs):
    """Numerical gradient. A vector result must have the same length as x."""
    point = _x(x)
    n = point.size
    current = _real(func(point, **kwargs))
    which = _side(side, n)
    elementwise = n == current.size
    if current.size != 1 and not elementwise:
        _stop("grad assumes a scalar valued function.")

    if method == "simple":
        args = _fill(_SIMPLE, method_args)
        which = np.array(which, copy=True)
        which[np.isnan(which)] = 1
        eps = _simple_eps(args["eps"], which)
        if elementwise:
            return (_real(func(point + eps, **kwargs)) - current) / eps
        df = np.full(n, np.nan)
        for i in range(n):
            moved = np.array(point, copy=True)
            moved[i] = moved[i] + eps[i]
            df[i] = _scalar((_real(func(moved, **kwargs)) - current) / eps[i])
        return df

    if method == "complex":
        if np.any(~np.isnan(which)):
            _stop("method 'complex' does not support non-NULL argument 'side'.")
        eps = _EPS
        try:
            value = func(point + eps * 1j, **kwargs)
        except Exception:
            _stop("function does not accept complex argument as required by method 'complex'.")
        if not np.iscomplexobj(value):
            _stop("function does not return a complex value as required by method 'complex'.")
        if elementwise:
            return np.imag(_complex(value)) / eps
        h0 = np.zeros(n, dtype=np.complex128)
        gradient = np.full(n, np.nan)
        for i in range(n):
            h0[i] = eps * 1j
            gradient[i] = _scalar(np.imag(_complex(func(point + h0, **kwargs))) / eps)
            h0[i] = 0
        return gradient

    if method != "Richardson":
        _stop(f"indicated method {method}not supported.")

    args = _fill(_GRAD_RICHARDSON, method_args)
    r = _whole(args["r"])
    v = args["v"]
    table = np.full((r, n), np.nan)
    h = _initial_h(point, args["d"], args["eps"], args["zero.tol"])
    for k in range(1, r + 1):
        ph, mh = _one_sided(h, which)
        if elementwise:
            table[k - 1, :] = (
                _real(func(point + ph, **kwargs)) - _real(func(point - mh, **kwargs))
            ) / (2 * h)
        else:
            for i in range(n):
                if k != 1 and abs(table[k - 2, i]) < 1e-20:
                    table[k - 1, i] = 0.0
                    continue
                mask = _unit(n, i)
                table[k - 1, i] = _scalar(
                    (
                        _real(func(point + ph * mask, **kwargs))
                        - _real(func(point - mh * mask, **kwargs))
                    )
                    / (2 * h[i])
                )
        if np.any(np.isnan(table[k - 1, :])):
            shown = " ".join(np.format_float_positional(float(item), unique=True, trim="k") for item in h)
            _stop(f"function returns NA at {shown} distance from x.")
        h = h / v
    if args["show.details"]:
        print("\n", "first order approximations", "\n")
        print(table)
    improved = table
    for m in range(1, r):
        four = 4.0 ** m
        improved = (improved[1 : r - m + 1] * four - improved[0 : r - m]) / (four - 1.0)
        if args["show.details"] and m != r - 1:
            print("\n", "Richarson improvement group No. ", m, "\n")
            print(improved)
    return np.ravel(improved)


def jacobian(func, x, method="Richardson", side=None, method_args=None, **kwargs):
    """Numerical Jacobian, one column per component of x."""
    point = _x(x)
    n = point.size
    current = _real(func(point, **kwargs))
    which = _side(side, n)
    rows = current.size

    if method == "simple":
        args = _fill(_SIMPLE, method_args)
        which = np.array(which, copy=True)
        which[np.isnan(which)] = 1
        eps = _simple_eps(args["eps"], which)
        df = np.full((rows, n), np.nan)
        for i in range(n):
            moved = np.array(point, copy=True)
            moved[i] = moved[i] + eps[i]
            df[:, i] = (_real(func(moved, **kwargs)) - current) / eps[i]
        return df

    if method == "complex":
        if np.any(~np.isnan(which)):
            _stop("method 'complex' does not support non-NULL argument 'side'.")
        eps = _EPS
        h0 = np.zeros(n, dtype=np.complex128)
        h0[0] = eps * 1j
        try:
            value = func(point + h0, **kwargs)
        except Exception:
            _stop("function does not accept complex argument as required by method 'complex'.")
        if not np.iscomplexobj(value):
            _stop("function does not return a complex value as required by method 'complex'.")
        h0[0] = 0
        jac = np.full((rows, n), np.nan)
        jac[:, 0] = np.imag(_complex(value)) / eps
        if n == 1:
            return jac
        for i in range(1, n):
            h0[i] = eps * 1j
            jac[:, i] = np.imag(_complex(func(point + h0, **kwargs))) / eps
            h0[i] = 0
        return jac

    if method != "Richardson":
        _stop(f"indicated method {method}not supported.")

    args = _fill(_GRAD_RICHARDSON, method_args)
    r = _whole(args["r"])
    v = args["v"]
    table = np.full((rows, r, n), np.nan)
    h = _initial_h(point, args["d"], args["eps"], args["zero.tol"])
    for _k in range(r):
        ph, mh = _one_sided(h, which)
        for i in range(n):
            mask = _unit(n, i)
            table[:, _k, i] = (
                _real(func(point + ph * mask, **kwargs))
                - _real(func(point - mh * mask, **kwargs))
            ) / (2 * h[i])
        h = h / v
    improved = table
    for m in range(1, r):
        four = 4.0 ** m
        improved = (
            improved[:, 1 : r - m + 1, :] * four - improved[:, 0 : r - m, :]
        ) / (four - 1.0)
    return np.array(improved[:, 0, :], dtype=float)


def genD(func, x, method="Richardson", method_args=None, **kwargs):
    """Bates and Watts D matrix. First p columns are the Jacobian."""
    if method != "Richardson":
        _stop("method not implemented.")
    args = _fill(_GEND_RICHARDSON, method_args)
    if args["v"] != 2:
        _stop("The current code assumes v is 2 (the default).")
    point = _x(x)
    f0 = _real(func(point, **kwargs))
    n = point.size
    r = _whole(args["r"])
    v = args["v"]
    d = args["d"]
    h0 = _initial_h(point, d, args["eps"], args["zero.tol"])
    columns = (n * (n + 3)) // 2
    D = np.zeros((f0.size, columns))
    d_approx = np.zeros((f0.size, r))
    h_diag = np.zeros((f0.size, n))
    h_approx = np.zeros((f0.size, r))
    for i in range(n):
        h = np.array(h0, copy=True)
        for k in range(r):
            step = _unit(n, i) * h
            f1 = _real(func(point + step, **kwargs))
            f2 = _real(func(point - step, **kwargs))
            d_approx[:, k] = (f1 - f2) / (2 * h[i])
            h_approx[:, k] = (f1 - 2 * f0 + f2) / h[i] ** 2
            h = h / v
        for m in range(1, r):
            four = 4.0 ** m
            for k in range(r - m):
                d_approx[:, k] = (d_approx[:, k + 1] * four - d_approx[:, k]) / (four - 1.0)
                h_approx[:, k] = (h_approx[:, k + 1] * four - h_approx[:, k]) / (four - 1.0)
        D[:, i] = d_approx[:, 0]
        h_diag[:, i] = h_approx[:, 0]
    u = n
    for i in range(n):
        for j in range(i + 1):
            if i == j:
                D[:, u] = h_diag[:, i]
            else:
                h = np.array(h0, copy=True)
                for k in range(r):
                    step = _unit(n, i) * h + _unit(n, j) * h
                    f1 = _real(func(point + step, **kwargs))
                    f2 = _real(func(point - step, **kwargs))
                    d_approx[:, k] = (
                        f1 - 2 * f0 + f2 - h_diag[:, i] * h[i] ** 2 - h_diag[:, j] * h[j] ** 2
                    ) / (2 * h[i] * h[j])
                    h = h / v
                for m in range(1, r):
                    four = 4.0 ** m
                    for k in range(r - m):
                        d_approx[:, k] = (d_approx[:, k + 1] * four - d_approx[:, k]) / (four - 1.0)
                D[:, u] = d_approx[:, 0]
            u += 1
    return Darray(
        D=D,
        p=n,
        f0=f0,
        func=func,
        x=point,
        d=d,
        method=method,
        method_args=args,
    )


def hessian(func, x, method="Richardson", method_args=None, **kwargs):
    """Numerical Hessian of a scalar function."""
    point = _x(x)
    if _real(func(point, **kwargs)).size != 1:
        _stop("Richardson method for hessian assumes a scalar valued function.")
    if method == "complex":
        args = _fill(
            {
                "eps": 1e-4,
                "d": 0.1,
                "zero.tol": _ZERO_TOL,
                "r": 4,
                "v": 2,
            },
            method_args,
        )

        def fn(at, **kw):
            return grad(
                func,
                at,
                method="complex",
                side=None,
                method_args={"eps": _EPS},
                **kw,
            )

        return jacobian(fn, point, method="Richardson", side=None, method_args=args, **kwargs)
    if method != "Richardson":
        _stop("method not implemented.")
    args = _fill(_HESS_RICHARDSON, method_args)
    D = genD(func, point, method=method, method_args=args, **kwargs)["D"]
    if D.shape[0] != 1:
        _stop("BUG! should not get here.")
    n = point.size
    H = np.zeros((n, n))
    u = n
    for i in range(n):
        for j in range(i + 1):
            H[i, j] = D[0, u]
            u += 1
    H = H + H.T
    diag = np.diag(H) / 2
    np.fill_diagonal(H, diag)
    return H
