"""Double and triple integrals, and quadrature over a triangle."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import Diag, ones

_EPS = float(np.finfo(float).eps)
_NODES7 = np.array(
    [
        -0.9604912687080202,
        -0.7745966692414834,
        -0.4342437493468026,
        0.0,
        0.4342437493468026,
        0.7745966692414834,
        0.9604912687080202,
    ]
)
_WT3 = np.array([0.0, 5.0 / 9.0, 0.0, 8.0 / 9.0, 0.0, 5.0 / 9.0, 0.0])
_WT7 = np.array(
    [
        0.1046562260264672,
        0.2684880898683334,
        0.4013974147759622,
        0.4509165386584744,
        0.4013974147759622,
        0.2684880898683334,
        0.1046562260264672,
    ]
)
_GK_X = np.array(
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
_GK_W = np.array(
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
_GK_X7 = _GK_X[np.array([1, 3, 5, 7, 9, 11, 13])]
_GK_W7 = np.array(
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


def dblquad(f, xa, xb, ya, yb, dim=2, subdivs=300, tol=None, **kwargs):
    xa = _scalar(xa, "xa")
    xb = _scalar(xb, "xb")
    ya = _scalar(ya, "ya")
    yb = _scalar(yb, "yb")
    if tol is None:
        tol = _EPS ** 0.5
    fun = _callable(f)

    def wrapped(x, y):
        return fun(x, y, **kwargs)

    trial = np.asarray(
        wrapped(np.array([xa, xb], dtype=float), np.array([ya, yb], dtype=float)),
        dtype=float,
    ).reshape(-1)
    if trial.size != 2:
        raise PracmaError("Function 'f' does not appear to be vectorized.")
    if dim == 2:
        def outer(xs):
            xs = np.asarray(xs, dtype=float).reshape(-1)
            return np.array(
                [
                    _stats_integrate(
                        lambda y, xx=x: wrapped(xx, y),
                        ya,
                        yb,
                        subdivisions=subdivs,
                        rel_tol=tol,
                    )
                    for x in xs
                ]
            )

        total = _stats_integrate(outer, xa, xb, subdivisions=subdivs, rel_tol=tol)
    elif dim == 1:
        def outer(ys):
            ys = np.asarray(ys, dtype=float).reshape(-1)
            return np.array(
                [
                    _stats_integrate(
                        lambda x, yy=y: wrapped(x, yy),
                        xa,
                        xb,
                        subdivisions=subdivs,
                        rel_tol=tol,
                    )
                    for y in ys
                ]
            )

        total = _stats_integrate(outer, ya, yb, subdivisions=subdivs, rel_tol=10.0 * tol)
    else:
        raise PracmaError("Argument 'dim' can only be 1 (x-) or 2 (y-variable first).")
    return np.float64(total)


def triplequad(f, xa, xb, ya, yb, za, zb, subdivs=300, tol=None, **kwargs):
    xa = _scalar(xa, "xa")
    xb = _scalar(xb, "xb")
    ya = _scalar(ya, "ya")
    yb = _scalar(yb, "yb")
    za = _scalar(za, "za")
    zb = _scalar(zb, "zb")
    if tol is None:
        tol = _EPS ** 0.5
    fun = _callable(f)

    def wrapped(x, y, z):
        return fun(x, y, z, **kwargs)

    def fyz(y, z):
        y = np.asarray(y, dtype=float).reshape(-1)
        z = np.asarray(z, dtype=float).reshape(-1)
        qin = np.zeros(y.size)
        for i in range(y.size):
            qin = _stats_integrate(
                lambda x, yi=y[i], zi=z[i]: wrapped(x, yi, zi),
                xa,
                xb,
                subdivisions=subdivs,
                rel_tol=1e-10,
            )
        return qin

    def vectorized(y, z):
        y = np.asarray(y, dtype=float).reshape(-1)
        z = np.asarray(z, dtype=float).reshape(-1)
        if y.size == 1 and z.size > 1:
            y = np.repeat(y, z.size)
        if z.size == 1 and y.size > 1:
            z = np.repeat(z, y.size)
        return np.array([fyz(np.array([yy]), np.array([zz])) for yy, zz in zip(y, z)], dtype=float)

    return dblquad(vectorized, ya, yb, za, zb, tol=tol)


def integral2(
    fun,
    xmin,
    xmax,
    ymin,
    ymax,
    sector=False,
    reltol=1e-6,
    abstol=0,
    maxlist=5000,
    singular=False,
    vectorized=True,
    **kwargs,
):
    xmin = _scalar(xmin, "xmin")
    xmax = _scalar(xmax, "xmax")
    if (
        math.isinf(xmin)
        or math.isinf(xmax)
        or (not callable(ymin) and _is_numeric_value(ymin) and math.isinf(float(np.asarray(ymin).reshape(-1)[0])))
        or (not callable(ymax) and _is_numeric_value(ymax) and math.isinf(float(np.asarray(ymax).reshape(-1)[0])))
    ):
        raise PracmaError("Borders of the integration domain cannot be infinite.")
    nlist = math.floor(float(maxlist) / 10.0)
    target = _callable(fun)
    if sector:
        def integrand(x, y):
            return target(y * np.cos(x), y * np.sin(x), **kwargs) * y
    else:
        def integrand(x, y):
            return target(x, y, **kwargs)
    phi_b = _bound_function(ymin, "ymin", two=False)
    phi_t = _bound_function(ymax, "ymax", two=False)
    if singular:
        theta_l, theta_r, phi_lo, phi_hi = 0.0, math.pi, 0.0, math.pi
    else:
        theta_l, theta_r, phi_lo, phi_hi = xmin, xmax, 0.0, 1.0
    area = (theta_r - theta_l) * (phi_hi - phi_lo)
    qsub, esub = _tensor(
        xmin, xmax, theta_l, theta_r, phi_lo, phi_hi, integrand, phi_b, phi_t, vectorized, singular
    )
    total = float(np.sum(qsub))
    tol = 100.0 * _EPS * abs(total)
    err_ok = 0.0
    adjust = 1.0
    main = np.zeros((int(nlist), 7))
    n_list = 0
    main, n_list, errbnd = _save2list(
        main, n_list, qsub, esub, theta_l, theta_r, phi_lo, phi_hi, tol, area, adjust, err_ok
    )
    if n_list == 0 or errbnd <= tol:
        return {"Q": np.float64(total), "error": np.float64(errbnd)}
    while True:
        main, n_list, entry = _next_entry(main, n_list)
        q = float(entry[0])
        e = float(entry[1])
        theta_l = float(entry[2])
        theta_r = float(entry[3])
        phi_lo = float(entry[4])
        phi_hi = float(entry[5])
        qsub, esub = _tensor(
            xmin, xmax, theta_l, theta_r, phi_lo, phi_hi, integrand, phi_b, phi_t, vectorized, singular
        )
        newq = float(np.sum(qsub))
        adjust = min(1.0, abs(q - newq) / e)
        total = total + (newq - q)
        tol = max(float(abstol), float(reltol) * abs(total)) / 8.0
        tol = max(tol, 100.0 * _EPS * abs(total))
        main, n_list, errbnd = _save2list(
            main, nlist, qsub, esub, theta_l, theta_r, phi_lo, phi_hi, tol, area, adjust, err_ok
        )
        if n_list == 0 or errbnd <= tol:
            break
        if n_list > maxlist:
            limit = max(float(abstol), max(100.0 * _EPS, float(reltol)) * abs(total))
            if errbnd > limit:
                raise PracmaError("Maximum number of subintervals: w/o convergence.")
            break
    return {"Q": np.float64(total), "error": np.float64(errbnd)}


def integral3(fun, xmin, xmax, ymin, ymax, zmin, zmax, reltol=1e-6, **kwargs):
    target = _callable(fun)

    def wrapped(x, y, z):
        return target(x, y, z, **kwargs)

    y_b = _bound_x(ymin, "ymin")
    y_t = _bound_x(ymax, "ymax")
    z_b = _bound_xy(zmin, "zmin")
    z_t = _bound_xy(zmax, "zmax")

    def fx(x):
        def z1(y, xx=x):
            return z_b(xx, y)

        def z2(y, xx=x):
            return z_t(xx, y)

        def fyz(y, z, xx=x):
            return wrapped(xx, y, z)

        return integral2(fyz, y_b(x), y_t(x), z1, z2, reltol=reltol)["Q"]

    def vectorized(xs):
        xs = np.asarray(xs, dtype=float).reshape(-1)
        return np.array([fx(x) for x in xs], dtype=float)

    total = _stats_integrate(vectorized, xmin, xmax, subdivisions=300, rel_tol=reltol)
    return np.float64(total)


def triquad(f, x, y, n=10, tol=1e-10, **kwargs):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size != 3 or y.size != 3:
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors of length 3.")
    count = math.floor(abs(float(n)))
    if count <= 2:
        raise PracmaError("Argument 'n' must be an integer greater or equal 2.")
    fun = _callable(f)

    def wrapped(xx, yy):
        return fun(xx, yy, **kwargs)

    vertices = np.column_stack([x, y])
    rel_tol = math.inf
    k = 1
    estimate = 0.0
    while rel_tol > tol and k <= 5:
        first = _tricoef(vertices, count)
        second = _tricoef(vertices, 2 * count + 1)
        i1 = _triangle_sum(wrapped, first)
        i2 = _triangle_sum(wrapped, second)
        rel_tol = abs(i1 - i2)
        estimate = i2
        k += 1
    return np.array([estimate], dtype=float)


def _triangle_sum(fun, grid):
    values = np.asarray(fun(grid["X"], grid["Y"]), dtype=float)
    total = grid["Wx"].reshape(1, -1) @ values @ grid["Wy"].reshape(-1, 1)
    return float(total.reshape(-1)[0])


def _tricoef(v, n):
    n = int(n)
    index = np.arange(1, n + 1, dtype=float)
    nnk = 2.0 * index + 1.0
    tail = 1.0 / (nnk * (nnk + 2.0))
    column_a = np.concatenate([np.array([1.0 / 3.0]), tail])
    upper = np.arange(2, n + 1, dtype=float)
    nnk_upper = nnk[1:]
    nk = upper + 1.0
    nnk2 = nnk_upper * nnk_upper
    beta = 4.0 * (upper * nk) ** 2 / (nnk2 * nnk2 - nnk2)
    column_b = np.concatenate([np.array([2.0, 2.0 / 9.0]), beta])
    ab = np.column_stack([column_a, column_b])
    s = np.sqrt(ab[1:n, 1])
    matrix = Diag(ab[:n, 0], 0) + Diag(s, -1) + Diag(s, 1)
    values, vectors = np.linalg.eigh(matrix)
    order = np.argsort(values)
    nodes = (values[order] + 1.0) / 2.0
    wx = ab[0, 1] * vectors[0, order] ** 2 / 4.0
    degree = n - 1
    n1 = degree + 1
    n2 = degree + 2
    descending = np.arange(degree, -1, -1, dtype=float)
    y = np.cos((2.0 * descending + 1.0) * math.pi / (2.0 * degree + 2.0))
    legendre = np.zeros((n1, n2))
    previous = np.array([2.0])
    while np.max(np.abs(y - previous)) > _EPS:
        legendre[:, 0] = 1.0
        legendre[:, 1] = y
        for k in range(2, n1 + 1):
            legendre[:, k] = ((2.0 * k - 1.0) * y * legendre[:, k - 1] - (k - 1.0) * legendre[:, k - 2]) / k
        lp = n2 * (legendre[:, n1 - 1] - y * legendre[:, n2 - 1]) / (1.0 - y * y)
        previous = y.copy()
        y = previous - legendre[:, n2 - 1] / lp
    cc = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 1.0], [0.0, 1.0, -1.0]]) @ v
    t1 = (1.0 + y) / 2.0
    weight_x = abs(np.linalg.det(cc[1:3, :])) * wx
    weight_y = 1.0 / ((1.0 - y * y) * lp * lp) * (n2 / n1) ** 2
    grid_x, grid_y = _meshgrid(t1, nodes)
    yy = grid_x * grid_y
    return {
        "X": cc[0, 0] + cc[1, 0] * grid_y + cc[2, 0] * yy,
        "Y": cc[0, 1] + cc[1, 1] * grid_y + cc[2, 1] * yy,
        "Wx": weight_x,
        "Wy": weight_y,
    }


def _tensor(a, b, theta_l, theta_r, phi_b, phi_t, fun, phi_bvar, phi_tvar, vectorized, singular):
    theta = _half_points(theta_l, theta_r)
    if singular:
        x = 0.5 * (b + a) + 0.5 * (b - a) * np.cos(theta)
    else:
        x = theta
    phi = _half_points(phi_b, phi_t).reshape(-1, 1)
    top = np.asarray(phi_tvar(x), dtype=float).reshape(-1)
    bottom = np.asarray(phi_bvar(x), dtype=float).reshape(-1)
    dydt = top - bottom
    if dydt.size == 1:
        dydt = np.repeat(float(dydt[0]), theta.size)
    if singular:
        t = 0.5 + 0.5 * np.cos(phi)
    else:
        t = phi
    ones_col = np.ones((theta.size, 1))
    grid_x = ones_col @ np.asarray(x, dtype=float).reshape(1, -1)
    grid_y = ones_col @ bottom.reshape(1, -1) + t.reshape(-1, 1) @ dydt.reshape(1, -1)
    if vectorized:
        values = np.asarray(fun(grid_x, grid_y), dtype=float)
    else:
        values = np.empty(grid_x.shape)
        for i in range(grid_x.shape[0]):
            for j in range(grid_x.shape[1]):
                values[i, j] = fun(grid_x[i, j], grid_y[i, j])
    if singular:
        temp = 0.25 * (b - a) * (
            np.sin(phi).reshape(-1, 1) @ (dydt.reshape(1, -1) * np.sin(theta).reshape(1, -1))
        )
    else:
        temp = ones_col @ dydt.reshape(1, -1)
    values = values * temp
    n = _NODES7.size
    blocks = (
        values[:n, :n],
        values[:n, n:],
        values[n:, :n],
        values[n:, n:],
    )
    dtheta = theta_r - theta_l
    dphi = phi_t - phi_b
    scale = (dtheta / 2.0) * (dphi / 2.0) / 4.0
    rough = np.array([_bilinear(_WT3, block) for block in blocks]) * scale
    fine = np.array([_bilinear(_WT7, block) for block in blocks]) * scale
    return fine.reshape(-1, 1), np.abs(rough - fine).reshape(-1, 1)


def _half_points(left, right):
    narray = 0.25 * np.column_stack([_NODES7, _NODES7])
    width = right - left
    centers = left + width * np.array([0.25, 0.75])
    extra = np.repeat(centers, _NODES7.size)
    return (width * narray + extra.reshape(narray.shape, order="F")).ravel(order="F")


def _bilinear(weights, block):
    return float(weights @ block @ weights)


def _save2list(main, n_list, qsub, esub, theta_l, theta_r, phi_b, phi_t, tol, area, adjust, err_ok):
    dtheta = theta_r - theta_l
    dphi = phi_t - phi_b
    localtol = tol * (dtheta / 2.0) * (dphi / 2.0) / area
    localtol = max(localtol, 100.0 * _EPS * abs(float(np.sum(qsub))))
    qvals = np.asarray(qsub, dtype=float).reshape(-1)
    evals = np.asarray(esub, dtype=float).reshape(-1)
    adjerr = adjust * evals
    if n_list + 4 > main.shape[0]:
        main = np.vstack([main, np.zeros((100, 7))])
    boxes = (
        (theta_l, theta_l + dtheta / 2.0, phi_b, phi_b + dphi / 2.0),
        (theta_l + dtheta / 2.0, theta_r, phi_b, phi_b + dphi / 2.0),
        (theta_l, theta_l + dtheta / 2.0, phi_b + dphi / 2.0, phi_t),
        (theta_l + dtheta / 2.0, theta_r, phi_b + dphi / 2.0, phi_t),
    )
    for i, box in enumerate(boxes):
        if adjerr[i] > localtol:
            n_list += 1
            main[n_list - 1, :] = (qvals[i], evals[i], box[0], box[1], box[2], box[3], adjerr[i])
        else:
            err_ok += adjerr[i]
    errbnd = err_ok + float(np.sum(main[:, 6]))
    return main, n_list, errbnd


def _next_entry(main, n_list):
    index = int(np.argmax(np.abs(main[:n_list, 6])))
    entry = main[index, :].copy()
    main = np.delete(main, index, axis=0)
    return main, n_list - 1, entry


def _bound_function(bound, name, two):
    if callable(bound):
        return bound
    if _is_numeric_value(bound):
        value = float(np.asarray(bound, dtype=float).reshape(-1)[0])

        def constant(x, level=value):
            size = _r_size(x)
            return level * ones(size[0], size[1])

        return constant
    if two:
        raise PracmaError(f"Argument '{name}' must be a constant or a function of x and y.")
    raise PracmaError(f"Argument '{name}' must be a constant or a (vectorized) function.")


def _bound_x(bound, name):
    if callable(bound):
        return bound
    if _is_numeric_value(bound):
        value = float(np.asarray(bound, dtype=float).reshape(-1)[0])

        def constant(x, level=value):
            return np.repeat(level, np.asarray(x).size)

        return constant
    raise PracmaError(f"Argument '{name}' must be a constant or a function of x.")


def _bound_xy(bound, name):
    if callable(bound):
        return bound
    if _is_numeric_value(bound):
        value = float(np.asarray(bound, dtype=float).reshape(-1)[0])

        def constant(x, y, level=value):
            return np.repeat(level, np.asarray(y).size)

        return constant
    raise PracmaError(f"Argument '{name}' must be a constant or a function of x and y.")


def _r_size(x):
    array = np.asarray(x)
    if array.ndim <= 1:
        return np.array([1.0, float(array.size)])
    return np.array(array.shape, dtype=float)


def _stats_integrate(func, lower, upper, subdivisions=100, rel_tol=None, abs_tol=None):
    if rel_tol is None:
        rel_tol = _EPS ** 0.25
    if abs_tol is None:
        abs_tol = rel_tol
    a = float(lower)
    b = float(upper)
    if a == b:
        return 0.0
    sign = 1.0
    if a > b:
        a, b = b, a
        sign = -1.0
    estimate, error = _gk_panel(func, a, b)
    panels = [(a, b, estimate, error)]
    total = estimate
    total_error = error
    while total_error > max(abs_tol, rel_tol * abs(total)) and len(panels) < int(subdivisions):
        index = max(range(len(panels)), key=lambda i: panels[i][3])
        left, right, piece, piece_error = panels.pop(index)
        mid = 0.5 * (left + right)
        q1, e1 = _gk_panel(func, left, mid)
        q2, e2 = _gk_panel(func, mid, right)
        total = total - piece + q1 + q2
        total_error = total_error - piece_error + e1 + e2
        panels.append((left, mid, q1, e1))
        panels.append((mid, right, q2, e2))
    return sign * total


def _gk_panel(func, a, b):
    half = 0.5 * (b - a)
    mid = 0.5 * (a + b)
    y15 = np.asarray(func(mid + half * _GK_X), dtype=float).reshape(-1)
    y7 = np.asarray(func(mid + half * _GK_X7), dtype=float).reshape(-1)
    q15 = half * float(np.sum(_GK_W * y15))
    q7 = half * float(np.sum(_GK_W7 * y7))
    return q15, abs(q15 - q7)


def _meshgrid(x, y):
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    columns = x.size
    rows = y.size
    grid_x = np.repeat(x, rows).reshape((rows, columns), order="F")
    grid_y = np.tile(y, columns).reshape((rows, columns), order="F")
    return grid_x, grid_y


def _is_numeric_value(value):
    if isinstance(value, (bool, np.bool_)):
        return False
    if callable(value):
        return False
    array = np.asarray(value)
    return array.dtype != object and np.issubdtype(array.dtype, np.number) and not np.iscomplexobj(array)


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
