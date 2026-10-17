"""Matrix helpers from corpcor: SVD, powers, rank, and symmetric packing."""

from __future__ import annotations

import warnings

import numpy as np

EPS = float(np.finfo(float).eps)
_MISSING = object()


class Matrix(np.ndarray):
    """A numeric matrix that can carry the attributes corpcor attaches."""

    def __new__(cls, data):
        return np.array(data, dtype=float, copy=True).view(cls)

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.scaled_center = getattr(obj, "scaled_center", None)
        self.scaled_scale = getattr(obj, "scaled_scale", None)
        self.lambda_value = getattr(obj, "lambda_value", None)
        self.lambda_estimated = getattr(obj, "lambda_estimated", None)
        self.lambda_var = getattr(obj, "lambda_var", None)
        self.lambda_var_estimated = getattr(obj, "lambda_var_estimated", None)
        self.spv = getattr(obj, "spv", None)
        self.shrinkage = getattr(obj, "shrinkage", False)


def as_matrix(x) -> np.ndarray:
    """R as.matrix. A one-dimensional sequence becomes a column."""
    array = np.asarray(x, dtype=float)
    if array.ndim == 0:
        array = array.reshape(1, 1)
    elif array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("x must be a matrix")
    return np.array(array, dtype=float, copy=True)


def match_arg(value: str, choices: tuple[str, ...]) -> str:
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) != 1:
        raise ValueError(f"`method` must be one of {', '.join(choices)}")
    return hits[0]


def r_round(value: float, digits: int = 4) -> str:
    """The text R's paste(round(x, digits)) prints."""
    text = f"{round(float(value), digits):.{digits}f}".rstrip("0").rstrip(".")
    if text in ("", "-0"):
        return "0"
    return text


def _svd_economy(m: np.ndarray, nu: bool = True, nv: bool = True):
    """R svd. v is the right vectors, not Vh."""
    u, d, vh = np.linalg.svd(m, full_matrices=False)
    v = vh.T
    if not nu:
        u = np.zeros((m.shape[0], 0))
    if not nv:
        v = np.zeros((m.shape[1], 0))
    return u, d, v


def positive_svd(m, tol=_MISSING):
    u, d, v = _svd_economy(as_matrix(m))
    if tol is _MISSING:
        tol = max(m.shape) * (d[0] if d.size else 0.0) * EPS
    keep = d > tol
    return {"d": d[keep], "u": u[:, keep], "v": v[:, keep]}


def nsmall_svd(m, tol=_MISSING):
    m = as_matrix(m)
    gram = m @ m.T
    u, d, _v = _svd_economy(gram, nv=False)
    if tol is _MISSING:
        tol = gram.shape[0] * (d[0] if d.size else 0.0) * EPS
    keep = d > tol
    d = np.sqrt(d[keep])
    u = u[:, keep]
    if d.size == 0:
        v = np.zeros((m.shape[1], 0))
    else:
        v = (m.T @ u) @ np.diag(1.0 / d)
    return {"d": d, "u": u, "v": v}


def psmall_svd(m, tol=_MISSING):
    m = as_matrix(m)
    gram = m.T @ m
    _u, d, v = _svd_economy(gram, nu=False)
    if tol is _MISSING:
        tol = gram.shape[0] * (d[0] if d.size else 0.0) * EPS
    keep = d > tol
    d = np.sqrt(d[keep])
    v = v[:, keep]
    if d.size == 0:
        u = np.zeros((m.shape[0], 0))
    else:
        u = (m @ v) @ np.diag(1.0 / d)
    return {"d": d, "u": u, "v": v}


def fast_svd(m, tol=_MISSING):
    """Singular values that stay positive, using the smaller Gram matrix when one side is short."""
    m = as_matrix(m)
    n, p = m.shape
    edge = 2
    if n > edge * p:
        return psmall_svd(m, tol)
    if edge * n < p:
        return nsmall_svd(m, tol)
    return positive_svd(m, tol)


def _symmetric_eigen(m: np.ndarray):
    """R eigen(symmetric=TRUE): values in decreasing order."""
    values, vectors = np.linalg.eigh(m)
    values = values[::-1]
    vectors = vectors[:, ::-1]
    return values, vectors


def mpower(m, alpha, pseudo=False, tol=_MISSING):
    """Power of a real symmetric matrix."""
    m = as_matrix(m)
    if np.any(np.abs(m - m.T) > 100 * EPS):
        raise ValueError("Input matrix is not symmetric!")
    values, vectors = _symmetric_eigen(m)
    if tol is _MISSING:
        tol = max(m.shape) * (np.max(np.abs(values)) if values.size else 0.0) * EPS
    values = values.copy()
    values[np.abs(values) <= tol] = 0.0
    if pseudo:
        keep = values != 0
    else:
        keep = np.ones(values.shape[0], dtype=bool)
    kept = values[keep]
    raised = _real_power(kept, alpha)
    basis = vectors[:, keep]
    if raised.size == 0:
        result = np.zeros_like(m)
    else:
        result = basis @ (raised[:, None] * basis.T)
    return result


def _real_power(values: np.ndarray, alpha: float) -> np.ndarray:
    """R's real power. A negative value to a non-integer power is missing."""
    out = np.empty(values.shape, dtype=float)
    integer = float(alpha).is_integer()
    for index, value in enumerate(values):
        if value < 0 and not integer:
            out[index] = np.nan
        elif value == 0 and alpha < 0:
            out[index] = np.inf
        else:
            out[index] = value ** alpha
    return out


def pseudoinverse(m, tol=_MISSING):
    """Moore-Penrose inverse from the positive singular values."""
    m = as_matrix(m)
    factors = fast_svd(m, tol)
    d = factors["d"]
    if d.size == 0:
        return np.zeros((m.shape[1], m.shape[0]))
    u = factors["u"]
    v = factors["v"]
    return v @ ((1.0 / d)[:, None] * u.T)


def _chol_upper(m: np.ndarray) -> bool:
    """R chol uses the upper triangle. NumPy factors the lower triangle."""
    try:
        np.linalg.cholesky(np.ascontiguousarray(m.T))
    except np.linalg.LinAlgError:
        return False
    return True


def is_positive_definite(m, tol=_MISSING, method="eigen"):
    """True when every eigenvalue, or the Cholesky factor, says the matrix is positive definite."""
    method = match_arg(method, ("eigen", "chol"))
    m = as_matrix(m)
    if method == "eigen":
        values, _vectors = _symmetric_eigen(m)
        if not np.isrealobj(values):
            warnings.warn("Input matrix has complex eigenvalues!", stacklevel=2)
            return False
        if tol is _MISSING:
            tol = max(m.shape) * (np.max(np.abs(values)) if values.size else 0.0) * EPS
        return bool(np.sum(values > tol) == values.size)
    # A successful chol() has class c("matrix", "array"). The installed
    # comparison class(val) == "try-error" then has length 2 and if() errors.
    # A failed chol() is class "try-error" and the function returns FALSE.
    if _chol_upper(m):
        raise ValueError("the condition has length > 1")
    return False


def make_positive_definite(m, tol=_MISSING):
    """Higham's correction that lifts nonpositive eigenvalues."""
    m = as_matrix(m)
    n = m.shape[0]
    if m.shape[1] != n:
        raise ValueError("Input matrix is not square!")
    values, vectors = _symmetric_eigen(m)
    if tol is _MISSING:
        tol = n * (np.max(np.abs(values)) if values.size else 0.0) * EPS
    delta = 2 * tol
    tau = np.maximum(0.0, delta - values)
    return m + vectors @ (tau[:, None] * vectors.T)


def rank_condition(m, tol=_MISSING):
    """Rank, condition number, and the tolerance used to decide them."""
    m = as_matrix(m)
    _u, d, _v = np.linalg.svd(m, full_matrices=False)
    if d.size == 0:
        return {"rank": 0, "condition": np.nan, "tol": 0.0}
    max_d = float(d[0])
    min_d = float(d[-1])
    if tol is _MISSING:
        tol = max(m.shape) * max_d * EPS
    rank = int(np.sum(d > tol))
    if rank < min(m.shape):
        min_d = 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        condition = max_d / min_d
    return {"rank": rank, "condition": float(condition), "tol": float(tol)}


def cov2cor(m):
    """R stats::cov2cor. The diagonal is set to 1."""
    m = as_matrix(m)
    if m.shape[0] != m.shape[1]:
        raise ValueError("'V' is not a square numeric matrix")
    scale = np.sqrt(1.0 / np.diag(m))
    if np.any(~np.isfinite(scale)):
        warnings.warn("diag(.) had 0 or NA entries; non-finite result is doubtful", stacklevel=2)
    result = scale[:, None] * m * scale[None, :]
    np.fill_diagonal(result, 1.0)
    return result


def rebuild_cov(r, v):
    """Covariance from a correlation matrix and a variance vector."""
    v = np.asarray(v, dtype=float)
    if np.any(v < 0):
        raise ValueError("Negative variance encountered!")
    sd = np.sqrt(v)
    r = as_matrix(r)
    return sd[:, None] * r * sd[None, :]


def decompose_cov(m):
    """Correlation matrix and the diagonal variances."""
    m = as_matrix(m)
    return {"r": cov2cor(m), "v": np.diag(m).copy()}


def rebuild_invcov(pr, pv):
    """Precision matrix from partial correlations and partial variances."""
    pv = np.asarray(pv, dtype=float)
    if np.any(pv < 0):
        raise ValueError("Negative partial variance encountered!")
    ipsd = np.sqrt(1.0 / pv)
    pr = as_matrix(pr)
    result = -ipsd[:, None] * pr * ipsd[None, :]
    np.fill_diagonal(result, -np.diag(result))
    return result


def decompose_invcov(m):
    """Partial correlations and partial variances of a precision matrix."""
    m = as_matrix(m)
    pv = 1.0 / np.diag(m)
    flipped = -m
    np.fill_diagonal(flipped, -np.diag(flipped))
    return {"pr": cov2cor(flipped), "pv": pv}


def _lower_index(n: int, diag: bool):
    rows = []
    cols = []
    for col in range(n):
        start = col if diag else col + 1
        for row in range(start, n):
            rows.append(row)
            cols.append(col)
    return np.asarray(rows, dtype=int), np.asarray(cols, dtype=int)


def sm2vec(m, diag=False):
    """Pack the lower triangle, column by column."""
    m = as_matrix(m)
    rows, cols = _lower_index(m.shape[0], diag)
    return m[rows, cols]


def sm_index(m, diag=False):
    """One-based row and column of each packed entry, matching sm2vec's order swapped."""
    m = as_matrix(m)
    n = m.shape[0]
    count = n * (n + 1) // 2 if diag else n * (n - 1) // 2
    index1 = np.empty(count, dtype=int)
    index2 = np.empty(count, dtype=int)
    delta = 0 if diag else 1
    z = 0
    for i in range(1, n - delta + 1):
        for j in range(i + delta, n + 1):
            index1[z] = i
            index2[z] = j
            z += 1
    return np.column_stack((index1, index2))


def vec2sm(vec, diag=False, order=None):
    """Unpack a vector into a symmetric matrix. Without the diagonal the diagonal is missing."""
    vec = np.asarray(vec, dtype=float).reshape(-1)
    n = (np.sqrt(1 + 8 * vec.size) + 1) / 2
    if diag:
        n = n - 1
    if np.ceil(n) != np.floor(n):
        raise ValueError("Length of vector incompatible with symmetric matrix")
    n = int(n)
    result = np.full((n, n), np.nan)
    rows, cols = _lower_index(n, diag)
    if order is None:
        result[rows, cols] = vec
    else:
        placed = np.empty(vec.size, dtype=float)
        placed[np.asarray(order, dtype=int) - 1] = vec
        result[rows, cols] = placed
    for i in range(n - 1):
        for j in range(i + 1, n):
            result[i, j] = result[j, i]
    return result
