"""Log-likelihoods for mvtnorm 1.4-2.

Triangular helpers come from ``mvtnorm._lt`` (the translation of
``ltMatrices.R``). This module imports that file lazily so it can be
loaded before ``_lt.py`` exists. The names below are the ones used here.

Callables
    ltMatrices(object, diag=False, byrow=False, names=True)
    is_ltMatrices(x)
    Lower_tri(x, diag=False, byrow=None)
    diagonals(x)
    set_diagonals(x, value)
    Dchol(x, D)
    invcholD(x, D=None)
    Mult(x, y=None, transpose=False)
    solve(a, b=MISSING, transpose=False)
    logdet(x)
    Tcrossprod(x, diag_only=False)
    vectrick(C, S=MISSING, A=MISSING, transpose=(True, True))
    as_chol(x)
    as_array(x)
    lt(J, diag=False)
    ut(J, diag=False)
    check_obs_mean(obs, mean, J, N)
    check_obs_invcholmean(obs, invcholmean, J, N)
    colSumsdnorm(z)
    subset_lt(x, i=None, j=None)

An ``ltMatrices`` value exposes ``diag``, ``byrow``, ``J``, ``rcnames``
(variable names), ``matnames`` (per-matrix names), and either itself as
the packed ``(n_elem, N)`` array or a ``packed`` attribute. ``vectrick``
returns an ``ltMatrices`` when ``S`` is one, and a plain ``(J**2, N)``
array when ``S`` is a numeric matrix. ``diagonals(j)`` for an integer
``j`` is the implicit identity of that order.
"""

from __future__ import annotations

import math
from contextlib import contextmanager

import numpy as np

from extradistr._rng import qnorm as _qnorm

_LOG_2PI = math.log(2.0 * math.pi)
_EPS = float(np.finfo(float).eps)
_SQRT2 = math.sqrt(2.0)

# C_pnorm_fast, West (SSRN 2842681). Literals match lpmvnorm.c.
_G2 = -0.0150234471495426236132
_G4 = 0.000666098511701018747289
_G6 = 5.07937324518981103694e-06
_G8 = -2.92345273673194627762e-06
_G10 = 1.34797733516989204361e-07
_M2DPI = -2.0 / math.pi


class _Missing:
    def __repr__(self) -> str:
        return "MISSING"


MISSING = _Missing()


def _mod():
    import mvtnorm._lt as mod

    return mod


def _fun(name):
    mod = _mod()
    if not hasattr(mod, name):
        raise AttributeError(f"mvtnorm._lt.{name} is required by the log-likelihood port")
    return getattr(mod, name)


def _attr(x, name):
    if hasattr(type(x), name) and isinstance(getattr(type(x), name), property):
        return getattr(x, name)
    if name in getattr(x, "__dict__", {}):
        return x.__dict__[name]
    attrs = getattr(x, "attrs", None)
    if isinstance(attrs, dict) and name in attrs:
        return attrs[name]
    if hasattr(x, name):
        val = getattr(x, name)
        if not callable(val):
            return val
    raise AttributeError(name)


def _unclass(x):
    if hasattr(x, "packed") and not isinstance(x, np.ndarray):
        arr = np.asarray(x.packed, dtype=float)
    elif hasattr(x, "unclass") and callable(x.unclass) and not isinstance(x, np.ndarray):
        arr = np.asarray(x.unclass(), dtype=float)
    else:
        arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape((-1, 1))
    return arr


def _diag(x) -> bool:
    return bool(_attr(x, "diag"))


def _byrow(x) -> bool:
    return bool(_attr(x, "byrow"))


def _J(x) -> int:
    try:
        return int(_attr(x, "J"))
    except AttributeError:
        n = _unclass(x).shape[0]
        d = 1 if _diag(x) else 0
        disc = (2 * d - 1) ** 2 + 8 * n
        return int(round((-(2 * d - 1) + math.sqrt(disc)) / 2))


def _dim(x):
    packed = _unclass(x)
    return (int(packed.shape[1]), _J(x), _J(x))


def _rcnames(x):
    for key in ("rcnames",):
        try:
            val = _attr(x, key)
        except AttributeError:
            continue
        if val is None or val is False:
            return None
        return list(val)
    return None


def _matnames(x):
    try:
        val = _attr(x, "matnames")
    except AttributeError:
        return None
    if val is None or val is False:
        return None
    return list(val)


def _is_lt(x) -> bool:
    try:
        return bool(_fun("is_ltMatrices")(x))
    except AttributeError:
        return hasattr(x, "diag") and hasattr(x, "byrow") and hasattr(x, "J")


def _rownames(x):
    if getattr(x, "rownames", None) is not None:
        return list(x.rownames)
    return None


def _colnames(x):
    if getattr(x, "colnames", None) is not None:
        return list(x.colnames)
    return None


def _is_matrix(x) -> bool:
    return isinstance(x, np.ndarray) and x.ndim == 2


def r_matrix(data, nrow=None, ncol=None) -> np.ndarray:
    """R ``matrix`` fill, column-major, recycling when the length requires it."""
    if _is_matrix(data) and nrow is None and ncol is None:
        return np.array(data, dtype=float, copy=True)
    flat = np.asarray(data, dtype=float).ravel(order="F")
    if nrow is None and ncol is None:
        return flat.reshape((-1, 1), order="F")
    if nrow is None:
        nrow = 0 if ncol == 0 else int(math.ceil(flat.size / ncol)) if flat.size else 0
        if flat.size and ncol and flat.size % ncol == 0:
            nrow = flat.size // ncol
    if ncol is None:
        ncol = 0 if nrow == 0 else int(math.ceil(flat.size / nrow)) if flat.size else 0
        if flat.size and nrow and flat.size % nrow == 0:
            ncol = flat.size // nrow
    need = int(nrow) * int(ncol)
    if flat.size == 0:
        flat = np.zeros(need)
    elif flat.size != need:
        flat = np.resize(flat, need)
    return flat.reshape((int(nrow), int(ncol)), order="F")


def _as_mat(x) -> np.ndarray:
    if _is_matrix(x):
        return np.array(x, dtype=float, copy=True)
    return r_matrix(x, ncol=1)


def _recycle(vec, shape) -> np.ndarray:
    flat = np.asarray(vec, dtype=float).ravel(order="F")
    need = int(np.prod(shape))
    if flat.size == need:
        return flat.reshape(shape, order="F")
    if flat.size == 0:
        return np.zeros(shape)
    return np.resize(flat, need).reshape(shape, order="F")


def r_div(a, b) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if b.shape == a.shape:
        return a / b
    return a / _recycle(b, a.shape)


def r_add(a, b) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if b.shape == a.shape:
        return a + b
    return a + _recycle(b, a.shape)


def r_sub(a, b) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if b.shape == a.shape:
        return a - b
    return a - _recycle(b, a.shape)


def _exp(x: float) -> float:
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


def _sqrt(x: float) -> float:
    if not math.isfinite(x) or x < 0.0:
        return math.nan
    return math.sqrt(x)


def _pnorm_fast(x: float, m: float) -> float:
    """``C_pnorm_fast`` from ``src/lpmvnorm.c``."""
    x = float(x)
    m = float(m)
    if not math.isfinite(x):
        return 1.0 if x > 0.0 else 0.0
    z = x - m
    z2 = z * z
    z4 = z2 * z2
    z6 = z4 * z2
    z8 = z6 * z2
    z10 = z8 * z2
    tmp = 1.0 + _G2 * z2 + _G4 * z4 + _G6 * z6 + _G8 * z8 + _G10 * z10
    tmp = _M2DPI * z2 * tmp
    sign = (z > 0.0) - (z < 0.0)
    return 0.5 + sign * _sqrt(1.0 - _exp(tmp)) / 2.0


def _pnorm_slow(x: float, m: float) -> float:
    x = float(x)
    m = float(m)
    z = (x - m) / _SQRT2
    try:
        return 0.5 * (1.0 + math.erf(z))
    except ValueError:
        return math.nan


def _dnorm(x: float, mean: float = 0.0, log: bool = False) -> float:
    x = float(x)
    mean = float(mean)
    z = x - mean
    logp = -0.5 * (z * z + _LOG_2PI)
    if log:
        return logp
    if not math.isfinite(logp):
        if math.isnan(logp):
            return math.nan
        return 0.0 if logp < 0 else math.inf
    return math.exp(logp)


def _pnorm_arr(x, mean=0.0) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    mean = np.asarray(mean, dtype=float)
    z = x - mean
    out = np.empty(np.broadcast(x, mean).shape, dtype=float)
    flat = np.broadcast_to(z, out.shape).ravel()
    dest = out.ravel()
    for i in range(dest.size):
        dest[i] = _pnorm_slow(float(flat[i]), 0.0)
    return out


def _dnorm_arr(x, mean=0.0) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    mean = np.asarray(mean, dtype=float)
    z = x - mean
    out = np.empty(np.broadcast(x, mean).shape, dtype=float)
    flat = np.broadcast_to(z, out.shape).ravel()
    dest = out.ravel()
    for i in range(dest.size):
        dest[i] = _dnorm(float(flat[i]), 0.0, False)
    return out


@contextmanager
def _seed_guard(seed):
    """Match the ``set.seed`` / ``on.exit`` pair copied from ``simulate.lm``."""
    if seed is None:
        yield
        return
    import boot.rng as rng

    saved = (rng._mti, list(rng._mt))
    try:
        rng.set_seed(int(seed))
        yield
    finally:
        rng._mti = saved[0]
        rng._mt[:] = saved[1]


def _unif() -> float:
    import boot.rng as rng

    return rng.unif()


def _stop(msg: str):
    raise ValueError(msg)


def _lpmvnorm_c_run(a, b, C, center, N, J, w, M, tol, log_lik, fast, per_obs, step):
    pnorm = _pnorm_fast if fast else _pnorm_slow
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if J > 1:
        n_off = J * (J - 1) // 2
        C = np.asarray(C, dtype=float)
        if C.ndim == 1 or C.shape[0] != n_off:
            C = np.asarray(C, dtype=float).reshape((n_off, -1), order="F")
    has_center = center is not None and np.size(center) > 0
    if has_center:
        center = np.asarray(center, dtype=float)
        if center.ndim == 1:
            center = center.reshape((J, N), order="F")
    q0 = _qnorm(tol)
    l0 = math.log(tol) if tol > 0 else -math.inf
    mdtol = 1.0 - tol
    iM = 0 if J == 1 else int(M)
    lM = 0.0 if J == 1 else math.log(float(M))
    out = np.zeros(1 if log_lik else N, dtype=float)
    y = np.zeros(max(J - 1, 1), dtype=float)
    for i in range(N):
        ic = i if step else 0
        x0 = -float(center[0, i]) if has_center else 0.0
        d0 = pnorm(float(a[0, i]), x0)
        e0 = pnorm(float(b[0, i]), x0)
        emd0 = e0 - d0
        intsum = emd0 if J == 1 else 0.0
        for m in range(iM):
            d = d0
            f = emd0
            emd = emd0
            start = 0
            for j in range(1, J):
                if w is None:
                    wtmp = _unif()
                else:
                    col = i * int(M) + m if per_obs else m
                    wtmp = float(w[j - 1, col])
                tmp = d + wtmp * emd
                if tmp < tol:
                    y[j - 1] = q0
                elif tmp > mdtol:
                    y[j - 1] = -q0
                else:
                    y[j - 1] = _qnorm(tmp)
                x = 0.0
                if has_center:
                    for k in range(j):
                        x += float(C[start + k, ic]) * (y[k] - float(center[k, i]))
                    x -= float(center[j, i])
                else:
                    for k in range(j):
                        x += float(C[start + k, ic]) * y[k]
                d = pnorm(float(a[j, i]), x)
                e = pnorm(float(b[j, i]), x)
                emd = e - d
                start += j
                f *= emd
            intsum += f
        if intsum < tol:
            logged = l0
        elif intsum > 0:
            logged = math.log(intsum)
        elif intsum == 0:
            logged = -math.inf
        else:
            logged = math.nan
        val = logged - lM
        if log_lik:
            out[0] += val
        else:
            out[i] = val
    return out


def _slpmvnorm_c(a, b, C, center, N, J, w, M, tol, fast):
    """``R_slpmvnorm`` in ``src/lpmvnorm.c``. Rows are intsum, chol, mean, lower, upper."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    pnorm = _pnorm_fast if fast else _pnorm_slow
    n_off = J * (J - 1) // 2
    Jp = J * (J + 1) // 2
    step = 0
    if J > 1:
        C = np.asarray(C, dtype=float)
        if C.ndim == 1:
            C = C.reshape((-1, 1))
        if C.size == n_off:
            C = C.reshape((n_off, 1), order="F")
            step = 0
        else:
            C = C.reshape((n_off, N), order="F")
            step = 1
    has_center = center is not None and np.size(center) > 0
    if has_center:
        center = np.asarray(center, dtype=float)
        if center.size != N * J:
            _stop("incorrect dimensions of center")
        center = center.reshape((J, N), order="F")
    per_obs = False
    if w is not None and J > 1:
        w = np.asarray(w, dtype=float)
        if w.size == (J - 1) * M:
            per_obs = False
        elif w.size == (J - 1) * N * M:
            per_obs = True
        else:
            _stop("Length of W incorrect")
        w = w.reshape((J - 1, -1), order="F")
    q0 = _qnorm(tol)
    mdtol = 1.0 - tol
    iM = 0 if J == 1 else int(M)
    ans = np.zeros((Jp + 1 + 3 * J, N), dtype=float)
    y = np.zeros(max(J - 1, 1), dtype=float)
    dp_c = np.zeros(Jp)
    ep_c = np.zeros(Jp)
    fp_c = np.zeros(Jp)
    dp_m = np.zeros(J)
    ep_m = np.zeros(J)
    fp_m = np.zeros(J)
    dp_l = np.zeros(J)
    ep_l = np.zeros(J)
    fp_l = np.zeros(J)
    dp_u = np.zeros(J)
    ep_u = np.zeros(J)
    fp_u = np.zeros(J)
    yp_c = np.zeros((Jp, max(J - 1, 1)))
    yp_m = np.zeros((J, max(J - 1, 1)))
    yp_l = np.zeros((J, max(J - 1, 1)))
    yp_u = np.zeros((J, max(J - 1, 1)))

    def _c11(ai, x0, cen0):
        if has_center:
            dp = _dnorm(ai, x0) * (ai - x0 - cen0) if math.isfinite(ai) else 0.0
            return dp
        return _dnorm(ai, x0) * (ai - x0) if math.isfinite(ai) else 0.0

    for i in range(N):
        ic = i if step else 0
        x0 = -float(center[0, i]) if has_center else 0.0
        cen0 = float(center[0, i]) if has_center else 0.0
        a0 = float(a[0, i])
        b0 = float(b[0, i])
        d0 = pnorm(a0, x0)
        e0 = pnorm(b0, x0)
        emd0 = e0 - d0
        intsum = emd0 if J == 1 else 0.0
        dp_c[0] = _c11(a0, x0, cen0)
        ep_c[0] = _c11(b0, x0, cen0)
        fp_c[0] = ep_c[0] - dp_c[0]
        dp_m[0] = _dnorm(a0, x0) if math.isfinite(a0) else 0.0
        ep_m[0] = _dnorm(b0, x0) if math.isfinite(b0) else 0.0
        dp_l[0] = dp_m[0]
        ep_u[0] = ep_m[0]
        dp_u[0] = 0.0
        ep_l[0] = 0.0
        fp_m[0] = ep_m[0] - dp_m[0]
        fp_l[0] = -dp_m[0]
        fp_u[0] = ep_m[0]
        if iM == 0:
            ans[0, i] = intsum
            ans[1, i] = fp_c[0]
            ans[2, i] = fp_m[0]
            ans[3, i] = fp_l[0]
            ans[4, i] = fp_u[0]
        for m in range(iM):
            d = d0
            f = emd0
            emd = emd0
            start = 0
            dp_c[0] = _c11(a0, x0, cen0)
            ep_c[0] = _c11(b0, x0, cen0)
            fp_c[0] = ep_c[0] - dp_c[0]
            dp_m[0] = _dnorm(a0, x0) if math.isfinite(a0) else 0.0
            ep_m[0] = _dnorm(b0, x0) if math.isfinite(b0) else 0.0
            dp_l[0] = dp_m[0]
            ep_u[0] = ep_m[0]
            dp_u[0] = 0.0
            ep_l[0] = 0.0
            fp_m[0] = ep_m[0] - dp_m[0]
            fp_l[0] = -dp_m[0]
            fp_u[0] = ep_m[0]
            for j in range(1, J):
                if w is None:
                    wtmp = _unif()
                else:
                    col = i * int(M) + m if per_obs else m
                    wtmp = float(w[j - 1, col])
                tmp = d + wtmp * emd
                if tmp < tol:
                    y[j - 1] = q0
                elif tmp > mdtol:
                    y[j - 1] = -q0
                else:
                    y[j - 1] = _qnorm(tmp)
                x = 0.0
                if has_center:
                    for k in range(j):
                        x += float(C[start + k, ic]) * (y[k] - float(center[k, i]))
                    x -= float(center[j, i])
                else:
                    for k in range(j):
                        x += float(C[start + k, ic]) * y[k]
                d = pnorm(float(a[j, i]), x)
                e = pnorm(float(b[j, i]), x)
                emd = e - d
                ytmp = _exp(-_dnorm(y[j - 1], 0.0, log=True))
                yp_c[:, j - 1] = 0.0
                n_prev = (j + 1) * j // 2
                for idx in range(n_prev):
                    yp_c[idx, j - 1] = ytmp * (dp_c[idx] + wtmp * (ep_c[idx] - dp_c[idx]))
                yp_m[:, j - 1] = 0.0
                yp_l[:, j - 1] = 0.0
                yp_u[:, j - 1] = 0.0
                for idx in range(j):
                    base_m = dp_m[idx] + wtmp * (ep_m[idx] - dp_m[idx])
                    yp_m[idx, j - 1] = ytmp * base_m
                    yp_l[idx, j - 1] = ytmp * (dp_l[idx] + wtmp * (dp_u[idx] - dp_l[idx]))
                    yp_u[idx, j - 1] = ytmp * (ep_l[idx] + wtmp * (ep_u[idx] - ep_l[idx]))
                aj = float(a[j, i])
                bj = float(b[j, i])
                dtmp = _dnorm(aj, x)
                ndtmp = -dtmp
                etmp = _dnorm(bj, x)
                netmp = -etmp
                for k in range(j):
                    idx = start + j + k
                    yk = y[k] - (float(center[k, i]) if has_center else 0.0)
                    dp_c[idx] = ndtmp * yk
                    ep_c[idx] = netmp * yk
                    fp_c[idx] = (ep_c[idx] - dp_c[idx]) * f
                idx = (j + 1) * (j + 2) // 2 - 1
                if has_center:
                    cenj = float(center[j, i])
                    dp_c[idx] = dtmp * (aj - x - cenj) if math.isfinite(aj) else 0.0
                    ep_c[idx] = etmp * (bj - x - cenj) if math.isfinite(bj) else 0.0
                else:
                    dp_c[idx] = dtmp * (aj - x) if math.isfinite(aj) else 0.0
                    ep_c[idx] = etmp * (bj - x) if math.isfinite(bj) else 0.0
                fp_c[idx] = (ep_c[idx] - dp_c[idx]) * f
                dp_m[j] = dtmp if math.isfinite(aj) else 0.0
                ep_m[j] = etmp if math.isfinite(bj) else 0.0
                dp_l[j] = dp_m[j]
                ep_u[j] = ep_m[j]
                dp_u[j] = 0.0
                ep_l[j] = 0.0
                fp_l[j] = -dp_m[j] * f
                fp_u[j] = ep_m[j] * f
                fp_m[j] = fp_u[j] + fp_l[j]
                for idx in range(j * (j + 1) // 2):
                    xx = 0.0
                    for k in range(j):
                        xx += float(C[start + k, ic]) * yp_c[idx, k]
                    dp_c[idx] = ndtmp * xx
                    ep_c[idx] = netmp * xx
                    fp_c[idx] = (ep_c[idx] - dp_c[idx]) * f + emd * fp_c[idx]
                for idx in range(j):
                    xx = 0.0
                    for k in range(j):
                        xx += float(C[start + k, ic]) * yp_m[idx, k]
                    dp_m[idx] = ndtmp * xx
                    ep_m[idx] = netmp * xx
                    fp_m[idx] = (ep_m[idx] - dp_m[idx]) * f + emd * fp_m[idx]
                    xx = 0.0
                    for k in range(j):
                        xx += float(C[start + k, ic]) * yp_l[idx, k]
                    dp_l[idx] = ndtmp * xx
                    dp_u[idx] = netmp * xx
                    fp_l[idx] = (dp_u[idx] - dp_l[idx]) * f + emd * fp_l[idx]
                    xx = 0.0
                    for k in range(j):
                        xx += float(C[start + k, ic]) * yp_u[idx, k]
                    ep_l[idx] = ndtmp * xx
                    ep_u[idx] = netmp * xx
                    fp_u[idx] = (ep_u[idx] - ep_l[idx]) * f + emd * fp_u[idx]
                start += j
                f *= emd
            ans[0, i] += f
            ans[1 : 1 + Jp, i] += fp_c
            ans[1 + Jp : 1 + Jp + J, i] += fp_m
            ans[1 + Jp + J : 1 + Jp + 2 * J, i] += fp_l
            ans[1 + Jp + 2 * J : 1 + Jp + 3 * J, i] += fp_u
    return ans


def _prepare_interval(lower, upper, mean, invcholmean, center, chol, invchol, M, w):
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    invchol_given = invchol is not MISSING
    if chol is MISSING:
        chol = _fun("solve")(invchol)
    lower = _as_mat(lower)
    upper = _as_mat(upper)
    if lower.shape != upper.shape:
        _stop("isTRUE(all.equal(dim(lower), dim(upper))) is not TRUE")
    if not _is_lt(chol):
        _stop("is.ltMatrices(chol) is not TRUE")
    byrow_orig = _byrow(chol)
    chol = _fun("ltMatrices")(chol, byrow=True)
    d = _dim(chol)
    N = int(lower.shape[1] if d[0] == 1 else d[0])
    J = int(d[1])
    if lower.shape != (J, N):
        _stop("nrow(lower) == J && ncol(lower) == N is not TRUE")
    if mean is not MISSING:
        lower = np.asarray(_fun("check_obs_mean")(lower, mean, J, N), dtype=float)
        upper = np.asarray(_fun("check_obs_mean")(upper, mean, J, N), dtype=float)
    if invcholmean is not MISSING:
        invcholmean = _fun("check_obs_invcholmean")(lower, invcholmean, J, N)
        center = -np.asarray(invcholmean, dtype=float)
    if center is not None:
        if not _is_matrix(center):
            center = r_matrix(center, nrow=J, ncol=N)
        else:
            center = np.asarray(center, dtype=float)
        if center.shape != (J, N):
            _stop("nrow(center) == J && ncol(center) == N is not TRUE")
    dchol = None
    if _diag(chol):
        dchol = np.asarray(_fun("diagonals")(chol), dtype=float)
        if dchol.ndim == 1:
            dchol = dchol.reshape((-1, 1))
        if not np.all(np.abs(dchol) > _EPS):
            _stop("all(abs(dchol) > (.Machine$double.eps)) is not TRUE")
        ac = r_div(lower, dchol)
        bc = r_div(upper, dchol)
        Cstd = _fun("Dchol")(chol, D=1.0 / dchol)
        if J > 1:
            uC = np.asarray(_fun("Lower_tri")(Cstd), dtype=float)
        else:
            uC = _unclass(Cstd)
    else:
        ac = lower
        bc = upper
        uC = np.asarray(_fun("Lower_tri")(chol), dtype=float)
    if w is not None and J > 1:
        w = np.asarray(w, dtype=float)
        if w.ndim == 1:
            w = w.reshape((w.shape[0], 1), order="F")
        if w.ndim != 2 or w.shape[0] != J - 1:
            _stop("is.matrix(w) && nrow(w) == J - 1 is not TRUE")
        if M is None:
            M = int(w.shape[1])
        else:
            M = int(M)
        if w.shape[1] not in (M, M * N):
            _stop("ncol(w) %in% c(M, M * N) is not TRUE")
    else:
        if J > 1:
            if M is None:
                _stop("either w or M must be specified")
            M = int(M)
        else:
            M = 1
    return {
        "ac": ac,
        "bc": bc,
        "uC": uC,
        "center": center,
        "N": N,
        "J": J,
        "M": M,
        "w": None if (w is None or J == 1) else w,
        "chol": chol,
        "byrow_orig": byrow_orig,
        "dchol": dchol,
        "invchol_given": invchol_given,
        "invcholmean_given": invcholmean is not MISSING,
    }


def lpmvnorm(
    lower,
    upper,
    mean=MISSING,
    invcholmean=MISSING,
    center=None,
    chol=MISSING,
    invchol=MISSING,
    logLik=True,
    M=None,
    w=None,
    seed=None,
    tol=None,
    fast=False,
):
    """Multivariate normal log-likelihood over intervals. R ``lpmvnorm``."""
    if tol is None:
        tol = _EPS
    with _seed_guard(seed):
        prep = _prepare_interval(lower, upper, mean, invcholmean, center, chol, invchol, M, w)
        return _lpmvnorm_c_run(
            prep["ac"],
            prep["bc"],
            prep["uC"] if prep["J"] > 1 else None,
            prep["center"],
            prep["N"],
            prep["J"],
            prep["w"],
            prep["M"],
            float(tol),
            bool(logLik),
            bool(fast),
            bool(prep["w"] is not None and prep["w"].shape[1] == prep["M"] * prep["N"]),
            0
            if prep["J"] == 1 or np.size(prep["uC"]) == prep["J"] * (prep["J"] - 1) // 2
            else 1,
        )


def _diag_index(J: int) -> np.ndarray:
    return np.cumsum(np.arange(1, J + 1)) - 1


def slpmvnorm(
    lower,
    upper,
    mean=MISSING,
    invcholmean=MISSING,
    center=None,
    chol=MISSING,
    invchol=MISSING,
    logLik=True,
    M=None,
    w=None,
    seed=None,
    tol=None,
    fast=False,
):
    """Score of ``lpmvnorm``. R ``slpmvnorm``."""
    if tol is None:
        tol = _EPS
    with _seed_guard(seed):
        prep = _prepare_interval(lower, upper, mean, invcholmean, center, chol, invchol, M, w)
        J = prep["J"]
        N = prep["N"]
        raw = _slpmvnorm_c(
            prep["ac"],
            prep["bc"],
            prep["uC"] if J > 1 else None,
            prep["center"],
            N,
            J,
            prep["w"],
            prep["M"],
            float(tol),
            bool(fast),
        )
        Jp = J * (J + 1) // 2
        intsum = raw[0, :].copy()
        ll = np.log(np.maximum(intsum, float(tol))) - math.log(float(prep["M"]))
        scores = raw[1:, :].copy()
        with np.errstate(divide="ignore", invalid="ignore"):
            scores = scores / intsum.reshape((1, -1))
        scores[:, intsum < float(tol)] = 0.0
        smean = -scores[Jp : Jp + J, :]
        slower = scores[Jp + J : Jp + 2 * J, :].copy()
        supper = scores[Jp + 2 * J : Jp + 3 * J, :].copy()
        ret = scores[:Jp, :].copy()
        dchol = prep["dchol"]
        if dchol is not None:
            smean = r_div(smean, dchol)
            slower = r_div(slower, dchol)
            supper = r_div(supper, dchol)
            reps = np.repeat(np.arange(J), np.arange(1, J + 1))
            ret = ret / dchol[reps, :]
            idx = _diag_index(J)
            ret[idx, :] *= -1.0
        else:
            idx = _diag_index(J)
        if prep["invchol_given"]:
            wrapped = _fun("ltMatrices")(
                ret, diag=True, byrow=True, names=_rcnames(prep["chol"])
            )
            ret = -_unclass(_fun("vectrick")(prep["chol"], wrapped))
        if dchol is None:
            ret = np.array(ret, dtype=float, copy=True)
            ret[idx, :] = 0.0
        ret = _fun("ltMatrices")(ret, diag=True, byrow=True, names=_rcnames(prep["chol"]))
        if prep["invcholmean_given"]:
            sinv = _fun("Mult")(prep["chol"], smean, transpose=True)
        ret = _fun("ltMatrices")(ret, byrow=prep["byrow_orig"])
        if not logLik:
            return ret
        out = {
            "logLik": ll,
            "mean": smean,
            "lower": slower,
            "upper": supper,
            "chol": ret,
        }
        if prep["invchol_given"]:
            out["invchol"] = out.pop("chol")
        if prep["invcholmean_given"]:
            out["invcholmean"] = sinv
        return out


def ldmvnorm(obs, mean=MISSING, invcholmean=MISSING, chol=MISSING, invchol=MISSING, logLik=True):
    """Exact multivariate normal log-likelihood. R ``ldmvnorm``."""
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    if mean is MISSING and invcholmean is MISSING:
        invcholmean = 0
    if (mean is MISSING) == (invcholmean is MISSING):
        _stop("xor(missing(mean), missing(invcholmean)) is not TRUE")
    obs = _as_mat(obs)
    if chol is not MISSING:
        if not _is_lt(chol):
            _stop("chol is not an object of class ltMatrices")
        d = _dim(chol)
        N = int(obs.shape[1] if d[0] == 1 else d[0])
        J = int(d[1])
        if invcholmean is MISSING:
            obs = np.asarray(_fun("check_obs_mean")(obs, mean, J, N), dtype=float)
            z = np.asarray(_fun("solve")(chol, obs), dtype=float)
        else:
            invcholmean = np.asarray(
                _fun("check_obs_invcholmean")(obs, invcholmean, J, N), dtype=float
            )
            z = np.asarray(_fun("solve")(chol, obs), dtype=float) - invcholmean
        logretval = np.asarray(_fun("colSumsdnorm")(z), dtype=float).ravel()
        if _diag(chol):
            ld = np.asarray(_fun("logdet")(chol), dtype=float).ravel()
            logretval = logretval - _recycle(ld, logretval.shape).ravel()
    else:
        if not _is_lt(invchol):
            _stop("invchol is not an object of class ltMatrices")
        d = _dim(invchol)
        N = int(obs.shape[1] if d[0] == 1 else d[0])
        J = int(d[1])
        if invcholmean is MISSING:
            obs = np.asarray(_fun("check_obs_mean")(obs, mean, J, N), dtype=float)
            z = np.asarray(_fun("Mult")(invchol, obs), dtype=float)
        else:
            invcholmean = np.asarray(
                _fun("check_obs_invcholmean")(obs, invcholmean, J, N), dtype=float
            )
            z = np.asarray(_fun("Mult")(invchol, obs), dtype=float) - invcholmean
        logretval = np.asarray(_fun("colSumsdnorm")(z), dtype=float).ravel()
        if _diag(invchol):
            ld = np.asarray(_fun("logdet")(invchol), dtype=float).ravel()
            logretval = logretval + _recycle(ld, logretval.shape).ravel()
    if logLik:
        return float(np.sum(logretval))
    return logretval


def _score_index(J, diag):
    mask = np.asarray(_fun("lt")(J, diag=diag), dtype=bool)
    rows = np.tile(np.arange(1, J + 1), (J, 1)).T
    idx = rows.ravel(order="F")[mask.ravel(order="F")]
    n = J if diag else J - 1
    j = np.arange(1, n + 1)
    idx2 = np.repeat(j, j[::-1])
    return idx.astype(int), idx2.astype(int)


def sldmvnorm(obs, mean=MISSING, invcholmean=MISSING, chol=MISSING, invchol=MISSING, logLik=True):
    """Score of ``ldmvnorm``. R ``sldmvnorm``."""
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    if mean is MISSING and invcholmean is MISSING:
        invcholmean = 0
    if (mean is MISSING) == (invcholmean is MISSING):
        _stop("xor(missing(mean), missing(invcholmean)) is not TRUE")
    obs = _as_mat(obs)
    if invchol is MISSING:
        invchol = _fun("solve")(chol)
        ret = sldmvnorm(obs=obs, mean=mean, invcholmean=invcholmean, invchol=invchol)
        ret["chol"] = _fun("as_chol")(_scale_packed(_fun("vectrick")(invchol, ret["invchol"]), -1.0))
        ret.pop("invchol", None)
        return ret
    d = _dim(invchol)
    N = int(obs.shape[1] if d[0] == 1 else d[0])
    J = int(d[1])
    inv_given = not (isinstance(invcholmean, (int, float)) and invcholmean == 0 and mean is MISSING)
    # missing invcholmean was replaced by 0 above only when mean was also missing.
    # Distinguish a user-supplied 0 from that default by the original missingness,
    # which was consumed. Re-read the R rule: after the default, missing() is false.
    # The caller of this inner branch always has invcholmean in hand. The score list
    # uses missing(invcholmean) from the original argument. Recover it: the default
    # assignment happens only when both were missing, and that 0 is indistinguishable
    # from an explicit 0. R treats both as not missing after assignment of the default
    # only for the xor check; missing() stays TRUE if the argument was missing even
    # after a local assignment... In R, `invcholmean <- 0` makes missing() FALSE.
    # So a defaulted 0 is NOT missing. Explicit 0 is also not missing. Both take the
    # invcholmean branch of the score list. The only missing case is when mean was
    # supplied. That is `invcholmean is MISSING` before the default. Recompute:
    return _sldmvnorm_inv(obs, mean, invcholmean, invchol, logLik, mean_was_missing=mean is MISSING)


def _scale_packed(x, factor):
    data = _unclass(x) * factor
    return _fun("ltMatrices")(data, diag=_diag(x), byrow=_byrow(x), names=_rcnames(x))


def _sldmvnorm_inv(obs, mean, invcholmean, invchol, logLik, mean_was_missing):
    """Body of ``sldmvnorm`` once ``invchol`` is in hand.

    ``mean_was_missing`` is the original ``missing(mean)``. After R's
    ``invcholmean <- 0`` default, ``missing(invcholmean)`` is false whenever
    mean was missing. When mean was supplied, invcholmean stays missing.
    """
    inv_missing = mean_was_missing is False and invcholmean is MISSING
    # If mean was supplied, invcholmean is missing (xor). If mean was missing,
    # invcholmean was set to 0 or supplied, so it is not missing.
    if mean is not MISSING:
        inv_missing = True
        if invcholmean is not MISSING:
            _stop("xor(missing(mean), missing(invcholmean)) is not TRUE")
    else:
        inv_missing = False
    d = _dim(invchol)
    N = int(obs.shape[1] if d[0] == 1 else d[0])
    J = int(d[1])
    if inv_missing:
        obs_c = np.asarray(_fun("check_obs_mean")(obs, mean, J, N), dtype=float)
        Mix = np.asarray(_fun("Mult")(invchol, obs_c), dtype=float)
        obs_for_lik = obs_c
        inv_for_lik = MISSING
    else:
        inv_m = np.asarray(_fun("check_obs_invcholmean")(obs, invcholmean, J, N), dtype=float)
        Mix = np.asarray(_fun("Mult")(invchol, obs), dtype=float) - inv_m
        obs_for_lik = obs
        inv_for_lik = inv_m
    sobs = -np.asarray(_fun("Mult")(invchol, Mix, transpose=True), dtype=float)
    idx, idx2 = _score_index(J, _diag(invchol))
    ret = -obs_for_lik[idx2 - 1, :] * Mix[idx - 1, :]
    # When invcholmean was used, the observations in the score are the original
    # ones, not a centered copy. R uses `obs` after the branch: centered only
    # in the mean branch.
    if inv_missing:
        obs_used = obs_for_lik
    else:
        obs_used = obs
    ret = -obs_used[idx2 - 1, :] * Mix[idx - 1, :]
    ret = _fun("ltMatrices")(ret, diag=_diag(invchol), byrow=False, names=_rcnames(invchol))
    ret = _fun("ltMatrices")(ret, diag=_diag(invchol), byrow=_byrow(invchol))
    if _diag(invchol):
        add = 1.0 / np.asarray(_fun("diagonals")(invchol), dtype=float)
        cur = np.asarray(_fun("diagonals")(ret), dtype=float)
        ret = _fun("set_diagonals")(ret, r_add(cur, add))
    else:
        ret = _fun("set_diagonals")(ret, 0)
    if inv_missing:
        out = {"obs": sobs, "invchol": ret}
    else:
        out = {"obs": sobs, "invcholmean": Mix, "invchol": ret}
    if logLik:
        if inv_missing:
            out["logLik"] = ldmvnorm(obs=obs_used, invchol=invchol, logLik=False)
        else:
            out["logLik"] = ldmvnorm(
                obs=obs, invcholmean=inv_for_lik, invchol=invchol, logLik=False
            )
    return out


def ldpmvnorm(
    obs=MISSING,
    lower=MISSING,
    upper=MISSING,
    mean=MISSING,
    invcholmean=MISSING,
    chol=MISSING,
    invchol=MISSING,
    logLik=True,
    **kwargs,
):
    """Mixed exact and interval log-likelihood. R ``ldpmvnorm``."""
    if obs is MISSING or obs is None:
        return lpmvnorm(
            lower=lower,
            upper=upper,
            mean=mean,
            invcholmean=invcholmean,
            chol=chol,
            invchol=invchol,
            logLik=logLik,
            **kwargs,
        )
    if (lower is MISSING and upper is MISSING) or (lower is None and upper is None):
        return ldmvnorm(
            obs=obs,
            mean=mean,
            invcholmean=invcholmean,
            chol=chol,
            invchol=invchol,
            logLik=logLik,
        )
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    obs = _as_mat(obs)
    lower = _as_mat(lower)
    upper = _as_mat(upper)
    cJ = obs.shape[0]
    dJ = lower.shape[0]
    N = obs.shape[1]
    if N != lower.shape[1] or N != upper.shape[1]:
        _stop("N == ncol(lower) is not TRUE")
    if mean is MISSING:
        cmean = 0
        dmean = 0
    else:
        if not _is_matrix(mean) or np.asarray(mean).shape[1] == 1:
            mean = r_matrix(mean, nrow=cJ + dJ, ncol=N)
        else:
            mean = np.asarray(mean, dtype=float)
        if mean.shape != (cJ + dJ, N):
            _stop("nrow(mean) == cJ + dJ is not TRUE")
        cmean = mean[:cJ, :]
        dmean = mean[cJ:, :]
    if invcholmean is not MISSING:
        _stop("missing(invcholmean) is not TRUE")
    if invchol is not MISSING:
        J = _dim(invchol)[1]
        if cJ + dJ != J:
            _stop("cJ + dJ == J is not TRUE")
        nm = _rcnames(invchol)
        rno = _rownames(obs)
        rnl = _rownames(lower)
        rnu = _rownames(upper)
        if rnl is not None and rnu is not None and rnl != rnu:
            _stop("isTRUE(all.equal(rnl, rnu)) is not TRUE")
        if rnl is not None and rno is not None and nm is not None and rno + rnl != list(nm):
            _stop("isTRUE(all.equal(c(rno, rnl), nm)) is not TRUE")
        md = _fun("marg_mvnorm")(invchol=invchol, which=list(range(1, cJ + 1)))
        ret = ldmvnorm(obs=obs, mean=cmean, invchol=md["invchol"], logLik=logLik)
        given = r_sub(obs, cmean) if not np.isscalar(cmean) else obs - cmean
        cd = _fun("cond_mvnorm")(
            invchol=invchol,
            which_given=list(range(1, cJ + 1)),
            given=given,
            center=True,
        )
        ret = ret + lpmvnorm(
            lower=lower,
            upper=upper,
            mean=dmean,
            invchol=cd["invchol"],
            center=cd["center"],
            logLik=logLik,
            **kwargs,
        )
        return ret
    J = _dim(chol)[1]
    if cJ + dJ != J:
        _stop("cJ + dJ == J is not TRUE")
    md = _fun("marg_mvnorm")(chol=chol, which=list(range(1, cJ + 1)))
    ret = ldmvnorm(obs=obs, mean=cmean, chol=md["chol"], logLik=logLik)
    given = obs - cmean if np.isscalar(cmean) else r_sub(obs, cmean)
    cd = _fun("cond_mvnorm")(
        chol=chol, which_given=list(range(1, cJ + 1)), given=given, center=True
    )
    ret = ret + lpmvnorm(
        lower=lower,
        upper=upper,
        mean=dmean,
        chol=cd["chol"],
        center=cd["center"],
        logLik=logLik,
        **kwargs,
    )
    return ret


def _r_index_vec(n, times=None, each=None) -> np.ndarray:
    base = np.arange(n)
    if each is not None:
        return np.repeat(base, each)
    if isinstance(times, (int, np.integer)):
        return np.tile(base, int(times))
    return np.repeat(base, times)


def sldpmvnorm(
    obs=MISSING,
    lower=MISSING,
    upper=MISSING,
    mean=MISSING,
    invcholmean=MISSING,
    chol=MISSING,
    invchol=MISSING,
    logLik=True,
    **kwargs,
):
    """Score of ``ldpmvnorm``. R ``sldpmvnorm``."""
    if obs is MISSING or obs is None:
        return slpmvnorm(
            lower=lower,
            upper=upper,
            mean=mean,
            invcholmean=invcholmean,
            chol=chol,
            invchol=invchol,
            logLik=logLik,
            **kwargs,
        )
    if (lower is MISSING and upper is MISSING) or (lower is None and upper is None):
        return sldmvnorm(
            obs=obs, mean=mean, invcholmean=invcholmean, chol=chol, invchol=invchol, logLik=logLik
        )
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    obs = _as_mat(obs)
    lower = _as_mat(lower)
    upper = _as_mat(upper)
    cJ = int(obs.shape[0])
    dJ = int(lower.shape[0])
    N = int(obs.shape[1])
    if N != lower.shape[1] or N != upper.shape[1]:
        _stop("N == ncol(lower) is not TRUE")
    if mean is MISSING:
        cmean = 0
        dmean = 0
    else:
        if not _is_matrix(mean) or np.asarray(mean).shape[1] == 1:
            mean = r_matrix(mean, nrow=cJ + dJ, ncol=N)
        else:
            mean = np.asarray(mean, dtype=float)
        if mean.shape != (cJ + dJ, N):
            _stop("nrow(mean) == cJ + dJ is not TRUE")
        cmean = mean[:cJ, :]
        dmean = mean[cJ:, :]
    if invcholmean is not MISSING:
        _stop("missing(invcholmean) is not TRUE")
    if invchol is MISSING:
        invchol = _fun("solve")(chol)
        ret = sldpmvnorm(
            obs=obs,
            lower=lower,
            upper=upper,
            mean=mean,
            invchol=invchol,
            logLik=logLik,
            **kwargs,
        )
        ret["chol"] = _fun("as_chol")(_scale_packed(_fun("vectrick")(invchol, ret["invchol"]), -1.0))
        ret.pop("invchol", None)
        return ret
    byrow_orig = _byrow(invchol)
    invchol = _fun("ltMatrices")(invchol, byrow=True)
    J = _dim(invchol)[1]
    if cJ + dJ != J:
        _stop("cJ + dJ == J is not TRUE")
    md = _fun("marg_mvnorm")(invchol=invchol, which=list(range(1, cJ + 1)))
    cs = sldmvnorm(obs=obs, mean=cmean, invchol=md["invchol"], logLik=logLik)
    obs_cmean = obs - cmean if np.isscalar(cmean) else r_sub(obs, cmean)
    cd = _fun("cond_mvnorm")(
        invchol=invchol,
        which_given=list(range(1, cJ + 1)),
        given=obs_cmean,
        center=True,
    )
    ds = slpmvnorm(
        lower=lower,
        upper=upper,
        mean=dmean,
        center=cd["center"],
        invchol=cd["invchol"],
        logLik=logLik,
        **kwargs,
    )
    tmp0 = np.asarray(_fun("solve")(cd["invchol"], ds["mean"], transpose=True), dtype=float)
    tmp = -tmp0[_r_index_vec(dJ, each=cJ), :] * obs_cmean[_r_index_vec(cJ, times=dJ), :]
    Jp = _unclass(invchol).shape[0]
    diag = _diag(invchol)
    M = np.asarray(_fun("as_array")(_fun("ltMatrices")(np.arange(1, Jp + 1), diag=diag, byrow=True)))
    if M.ndim == 2:
        M = M[:, :, None]
    M = M[:, :, 0]
    ret = np.zeros((Jp, N), dtype=float)
    M1 = M[:cJ, :cJ]
    ut = np.asarray(_fun("ut")(cJ, diag=diag), dtype=bool)
    idx = M1.T.ravel(order="F")[ut.ravel(order="F")].astype(int)
    block = np.asarray(_fun("Lower_tri")(cs["invchol"], diag=diag), dtype=float)
    ret[idx - 1, :] = block
    idx = M[cJ:, :cJ].T.ravel(order="F").astype(int)
    ret[idx - 1, :] = tmp
    M3 = M[cJ:, cJ:]
    ut3 = np.asarray(_fun("ut")(M3.shape[0], diag=diag), dtype=bool)
    idx = M3.T.ravel(order="F")[ut3.ravel(order="F")].astype(int)
    ret[idx - 1, :] = np.asarray(_fun("Lower_tri")(ds["invchol"], diag=diag), dtype=float)
    ret_lt = _fun("ltMatrices")(ret, diag=diag, byrow=True)
    if not diag:
        ret_lt = _fun("set_diagonals")(ret_lt, 0)
    ret_lt = _fun("ltMatrices")(ret_lt, byrow=byrow_orig)
    aL = np.asarray(_fun("as_array")(invchol), dtype=float)
    if aL.ndim == 2:
        aL = aL[:, :, None]
    aL = aL[cJ:, :cJ, :]
    lst = tmp0[_r_index_vec(dJ, times=cJ), :]
    if aL.shape[2] == 1 and lst.shape[1] != 1:
        aL = np.repeat(aL, lst.shape[1], axis=2)
    filled = _recycle(lst, aL.shape)
    dobs = -(aL * filled).sum(axis=0)
    out = {
        "invchol": ret_lt,
        "obs": np.asarray(cs["obs"], dtype=float) + dobs,
        "lower": ds["lower"],
        "upper": ds["upper"],
    }
    if logLik:
        out["logLik"] = np.asarray(cs["logLik"], dtype=float) + np.asarray(ds["logLik"], dtype=float)
    out["mean"] = np.vstack([-out["obs"], np.asarray(ds["mean"], dtype=float)])
    return out


def deperma(
    chol=MISSING,
    permuted_chol=MISSING,
    invchol=MISSING,
    permuted_invchol=MISSING,
    perm=MISSING,
    score_schol=MISSING,
):
    """Map a permuted Cholesky score back. R ``deperma``."""
    if chol is MISSING:
        if invchol is MISSING:
            _stop("chol = solve(invchol) needs invchol")
        chol = _fun("solve")(invchol)
    if permuted_chol is MISSING:
        if permuted_invchol is MISSING:
            _stop("permuted_chol = solve(permuted_invchol) needs permuted_invchol")
        permuted_chol = _fun("solve")(permuted_invchol)
    if not _is_lt(chol) or not _is_lt(permuted_chol):
        _stop("is.ltMatrices(chol) is not TRUE")
    byrow_orig = _byrow(chol)
    chol = _fun("ltMatrices")(chol, byrow=False)
    permuted_chol = _fun("ltMatrices")(permuted_chol, byrow=False)
    if _dim(chol) != _dim(permuted_chol):
        _stop("max(abs(dim(chol) - dim(permuted_chol))) == 0 is not TRUE")
    J = _dim(chol)[1]
    if not _diag(chol):
        _stop('attr(chol, "diag") is not TRUE')
    inv_given = invchol is not MISSING
    if perm is MISSING:
        return score_schol
    perm = np.asarray(perm, dtype=int).ravel()
    if not np.array_equal(np.sort(perm), np.arange(1, J + 1)):
        _stop("isTRUE(all.equal(sort(perm), 1:J)) is not TRUE")
    if np.max(np.abs(perm - np.arange(1, J + 1))) == 0:
        return score_schol
    if not _is_lt(score_schol):
        _stop("is.matrix(score_schol) is not TRUE")
    byrow_orig_s = _byrow(score_schol)
    score = _unclass(_fun("ltMatrices")(score_schol, byrow=False))
    if score.shape[0] != J * (J + 1) // 2:
        _stop("J * (J + 1) / 2 == nrow(score_schol) is not TRUE")
    idx = np.arange(1, J * J + 1).reshape((J, J), order="F")
    tidx = idx.T.ravel(order="F").astype(int)
    lt_mask = np.asarray(_fun("lt")(J, diag=True), dtype=bool)
    ltT = idx.ravel(order="F")[lt_mask.ravel(order="F")].astype(int)
    P = np.zeros((J, J))
    P[np.arange(J), perm - 1] = 1.0
    ID = np.eye(J)
    IDP = np.kron(ID, P)
    Nc = _dim(chol)[0]
    full_c = np.asarray(_fun("as_array")(chol), dtype=float)
    full_p = np.asarray(_fun("as_array")(permuted_chol), dtype=float)
    if full_c.ndim == 2:
        full_c = full_c[:, :, None]
        full_p = full_p[:, :, None]
    mC = full_c[perm - 1, :, :]
    parts = []
    for i in range(Nc):
        Mi = mC[:, :, i]
        Ci = full_p[:, :, i]
        B1 = np.kron(Mi, ID) + np.kron(ID, Mi)[:, tidx - 1]
        B1 = B1 @ IDP
        B1 = B1[:, ltT - 1]
        B2 = np.kron(Ci, ID) + np.kron(ID, Ci)[:, tidx - 1]
        B2 = B2[:, ltT - 1]
        try:
            B3 = np.linalg.solve(B2.T @ B2, B2.T @ B1)
        except np.linalg.LinAlgError as exc:
            _stop("failure computing permutation score")
            raise exc
        if Nc == 1:
            parts.append(score.T @ B3)
        else:
            parts.append(score[:, i : i + 1].T @ B3)
    stacked = np.vstack(parts)
    ret = _fun("ltMatrices")(stacked.T, diag=True, byrow=False)
    if inv_given:
        ret = _scale_packed(_fun("vectrick")(chol, ret), -1.0)
    return _fun("ltMatrices")(ret, byrow=byrow_orig_s)


def standardize(chol=MISSING, invchol=MISSING):
    """Correlation-scale Cholesky. R ``standardize``."""
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    if invchol is not MISSING:
        return _fun("invcholD")(invchol)
    return _fun("Dchol")(chol)


def destandardize(chol=MISSING, invchol=MISSING, score_schol=MISSING):
    """Map a correlation-scale score back to a covariance Cholesky. R ``destandardize``."""
    if chol is MISSING:
        if invchol is MISSING:
            _stop("chol = solve(invchol) needs invchol")
        chol = _fun("solve")(invchol)
    if not _is_lt(chol):
        _stop("is.ltMatrices(chol) is not TRUE")
    J = _dim(chol)[1]
    byrow_orig = _byrow(chol)
    chol = _fun("ltMatrices")(chol, byrow=False)
    if _is_lt(score_schol):
        arr = np.asarray(_fun("as_array")(score_schol), dtype=float)
        if arr.ndim == 2:
            arr = arr[:, :, None]
        score = np.column_stack([arr[:, :, i].ravel(order="F") for i in range(arr.shape[2])])
    else:
        score = np.asarray(score_schol, dtype=float)
        if score.ndim == 1:
            score = score.reshape((-1, 1))
    if not _is_matrix(score):
        _stop("is.matrix(score_schol) is not TRUE")
    N = score.shape[1]
    if score.shape[0] != J * J:
        _stop("J^2 == nrow(score_schol) is not TRUE")
    CCt = np.asarray(_fun("Tcrossprod")(chol, diag_only=True), dtype=float)
    if CCt.ndim == 1:
        CCt = CCt.reshape((-1, 1))
    Dinv = 1.0 / np.sqrt(CCt)
    DC = _fun("Dchol")(chol, D=Dinv)
    # SDC <- solve(DC) is unused by the arithmetic that follows.
    M = np.arange(1, J * J + 1).reshape((J, J), order="F")
    IDX = M.T.ravel(order="F").astype(int)
    i = np.cumsum(np.concatenate([[1], np.repeat(J + 1, J - 1)])).astype(int)
    ID = _fun("diagonals")(int(J), byrow=False)
    if _dim(ID)[0] != _dim(chol)[0]:
        ID = _fun("subset_lt")(ID, i=np.repeat(1, _dim(chol)[0]))
    B = np.asarray(_fun("vectrick")(ID, score, chol), dtype=float)
    mult = (-0.5) * np.power(CCt.ravel(order="F"), -1.5)
    B = np.array(B, dtype=float, copy=True)
    B[i - 1, :] *= mult.reshape((J, B.shape[1]), order="F")
    keep = np.zeros(B.shape[0], dtype=bool)
    keep[i - 1] = True
    B[~keep, :] = 0.0
    Dtmp = _fun("Dchol")(ID, D=Dinv)
    part = np.asarray(_fun("vectrick")(ID, B, chol, transpose=(True, False)), dtype=float)
    part = part + np.asarray(_fun("vectrick")(chol, B, ID), dtype=float)[IDX - 1, :]
    part = part + np.asarray(_fun("vectrick")(Dtmp, score, ID), dtype=float)
    if invchol is not MISSING:
        # R evaluates `- vectrick(chol, ret)` while ret is still the full J^2
        # matrix, so S is numeric and the result is a plain matrix.
        part = -np.asarray(_fun("vectrick")(chol, part), dtype=float)
    lt_mask = np.asarray(_fun("lt")(J, diag=False), dtype=bool)
    rows = M.ravel(order="F")[lt_mask.ravel(order="F")].astype(int)
    part = part[rows - 1, :]
    ret = _fun("ltMatrices")(part, diag=False, byrow=False, names=_rcnames(chol))
    ret = _fun("ltMatrices")(ret, byrow=byrow_orig)
    return _fun("set_diagonals")(ret, 0)


def lpRR(lower=MISSING, upper=MISSING, mean=0, B=MISSING, D=None, Z=None, weights=None, log_p=True):
    """Reduced-rank interval log-likelihood. R ``lpRR``."""
    if B is MISSING:
        _stop("!missing(B) is not TRUE")
    B = _as_mat(B) if not _is_matrix(np.asarray(B, dtype=float)) else np.asarray(B, dtype=float)
    if np.asarray(B).ndim == 1:
        B = r_matrix(B, ncol=1)
    J = B.shape[0]
    if D is None:
        D = np.ones(J)
    D = np.asarray(D, dtype=float).ravel()
    Dsqrt = np.sqrt(D)
    Z = np.asarray(Z, dtype=float)
    if Z.ndim == 1:
        Z = Z.reshape((-1, 1))
    if Z.shape[0] != B.shape[1]:
        _stop("nrow(Z) == K is not TRUE")
    if weights is None:
        weights = 1.0 / Z.shape[1]
    weights = np.asarray(weights, dtype=float).ravel()
    if weights.size not in (1, Z.shape[1]):
        _stop("length(weights) == 1 || length(weights) == ncol(Z) is not TRUE")
    BZ = (B / Dsqrt[:, None]) @ Z
    if lower is MISSING:
        pl = 0.0
    else:
        lower = np.asarray(lower, dtype=float).ravel()
        if lower.size != J:
            _stop("length(lower) == J is not TRUE")
        lower = (lower - np.asarray(mean, dtype=float)) / Dsqrt
        pl = _pnorm_arr(lower[:, None] - BZ)
    if upper is MISSING:
        pl = 0.0
        pu = None
    else:
        upper = np.asarray(upper, dtype=float).ravel()
        if upper.size != J:
            _stop("length(upper) == J is not TRUE")
        upper = (upper - np.asarray(mean, dtype=float)) / Dsqrt
        pu = _pnorm_arr(upper[:, None] - BZ)
    if pu is None:
        _stop("object 'pu' not found")
    inner = np.maximum(0.0, pu - pl)
    with np.errstate(divide="ignore", invalid="ignore"):
        col = np.nansum(np.log(inner), axis=0)
        retw = weights * np.exp(col)
    total = float(np.sum(retw))
    if log_p:
        top = np.max(np.array([0.0, total], dtype=float))
        with np.errstate(divide="ignore", invalid="ignore"):
            return float(np.log(top))
    return total


def slpRR(lower=MISSING, upper=MISSING, mean=0, B=MISSING, D=None, Z=None, weights=None, log_p=True):
    """Score of ``lpRR``. R ``slpRR``."""
    if B is MISSING:
        _stop("!missing(B) is not TRUE")
    B = np.asarray(B, dtype=float)
    if B.ndim == 1:
        B = r_matrix(B, ncol=1)
    J = B.shape[0]
    K = B.shape[1]
    if D is None:
        D = np.ones(J)
    D = np.asarray(D, dtype=float).ravel()
    Dsqrt = np.sqrt(D)
    Z = np.asarray(Z, dtype=float)
    if Z.ndim == 1:
        Z = Z.reshape((-1, 1))
    if Z.shape[0] != K:
        _stop("nrow(Z) == K is not TRUE")
    if weights is None:
        weights = 1.0 / Z.shape[1]
    weights = np.asarray(weights, dtype=float).ravel()
    if weights.size not in (1, Z.shape[1]):
        _stop("length(weights) == 1 || length(weights) == ncol(Z) is not TRUE")
    BZ = (B / Dsqrt[:, None]) @ Z
    if lower is MISSING:
        pl = 0.0
        lBZ = None
    else:
        lower = np.asarray(lower, dtype=float).ravel()
        if lower.size != J:
            _stop("length(lower) == J is not TRUE")
        lower = (lower - np.asarray(mean, dtype=float)) / Dsqrt
        lBZ = lower[:, None] - BZ
        pl = _pnorm_arr(lBZ)
    if upper is MISSING:
        pl = 0.0
        pu = None
        uBZ = None
    else:
        upper = np.asarray(upper, dtype=float).ravel()
        if upper.size != J:
            _stop("length(upper) == J is not TRUE")
        upper = (upper - np.asarray(mean, dtype=float)) / Dsqrt
        uBZ = upper[:, None] - BZ
        pu = _pnorm_arr(uBZ)
    if pu is None or lBZ is None or uBZ is None:
        _stop("object 'pu' not found")
    inner = np.maximum(0.0, pu - pl)
    with np.errstate(divide="ignore", invalid="ignore"):
        retw = weights * np.exp(np.nansum(np.log(inner), axis=0))
        dlBZ = _dnorm_arr(lBZ)
        duBZ = _dnorm_arr(uBZ)
        d = retw.reshape((1, -1)) / inner
        db = d * (duBZ - dlBZ)
        tdb = db.T
        cols = [np.nansum(tdb * Z[r, :, None], axis=0) for r in range(Z.shape[0])]
        dB = -np.column_stack(cols) / Dsqrt[:, None]
        Du = (-0.5 / D)[:, None] * uBZ
        Dl = (-0.5 / D)[:, None] * lBZ
        dD = np.nansum(d * duBZ * Du, axis=1) - np.nansum(d * dlBZ * Dl, axis=1)
        dl = -np.nansum(d * dlBZ, axis=1) / Dsqrt
        du = np.nansum(d * duBZ, axis=1) / Dsqrt
        dm = -du - dl
    fct = 1.0 / float(np.sum(retw)) if log_p else 1.0
    return {
        "lower": fct * dl,
        "upper": fct * du,
        "mean": fct * dm,
        "B": fct * dB,
        "D": fct * dD,
    }
