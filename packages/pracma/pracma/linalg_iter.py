"""Tridiagonal, stationary, and GMRES solvers."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.arrays import eye, zeros
from pracma.linalg_internal import frobenius, is_matrix, is_numeric, length, match_arg
from pracma.linalg_tri import tril


def trisolve(a, b, d, rhs):
    for label, value in (("a", a), ("b", b), ("d", d), ("rhs", rhs)):
        if not is_numeric(value):
            raise PracmaError(f"is.numeric({label}) is not TRUE")
    diag = np.array(a, dtype=float).reshape(-1)
    if diag.size < 3:
        raise PracmaError("Argument 'n' must be greater or equal 3.")
    if np.array(b).size != diag.size - 1 or np.array(d).size != diag.size - 1:
        raise PracmaError("Vectors 'b' and 'd' must be of a length of length(a)-1.")
    if np.array(rhs).size != diag.size:
        raise PracmaError("Vector 'rhs' must be of the same length as 'a'.")
    return _trisolve_body(a, b, d, rhs)


def _trisolve_body(a, b, d, rhs):
    diag = np.array(a, dtype=float, copy=True).reshape(-1)
    superdiag = np.concatenate([np.array(b, dtype=float, copy=True).reshape(-1), np.zeros(1)])
    subdiag = np.array(d, dtype=float, copy=True).reshape(-1)
    x = np.array(rhs, dtype=float, copy=True).reshape(-1)
    n = diag.size
    for i in range(n - 1):
        if subdiag[i] != 0:
            t = diag[i] / subdiag[i]
            si = 1.0 / np.sqrt(1 + t * t)
            co = t * si
            diag[i] = diag[i] * co + subdiag[i] * si
            h = superdiag[i]
            superdiag[i] = h * co + diag[i + 1] * si
            diag[i + 1] = -h * si + diag[i + 1] * co
            subdiag[i] = superdiag[i + 1] * si
            superdiag[i + 1] = superdiag[i + 1] * co
            h = x[i]
            x[i] = h * co + x[i + 1] * si
            x[i + 1] = -h * si + x[i + 1] * co
    if np.any(diag == 0.0):
        raise PracmaError("Triangular matrix is singular -- system not solvable.")
    x[n - 1] = x[n - 1] / diag[n - 1]
    x[n - 2] = (x[n - 2] - superdiag[n - 2] * x[n - 1]) / diag[n - 2]
    for i in range(n - 3, -1, -1):
        x[i] = (x[i] - superdiag[i] * x[i + 1] - subdiag[i] * x[i + 2]) / diag[i]
    return x


def itersolve(A, b, x0=None, nmax=1000, tol=float(np.finfo(float).eps) ** 0.5, method="Gauss-Seidel"):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_numeric(b):
        raise PracmaError("is.numeric(b) is not TRUE")
    matrix = np.array(A, dtype=float, copy=False)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise PracmaError("Argument 'A' must be a square, positive definite matrix.")
    n = matrix.shape[0]
    rhs = np.array(b, dtype=float).reshape(-1)
    if rhs.size != n:
        raise PracmaError("Argument 'b' must have the length 'n = ncol(A) = nrow(A).")
    if x0 is None:
        start = np.zeros(n)
    else:
        if not is_numeric(x0):
            raise PracmaError("is.numeric(x0) is not TRUE")
        start = np.array(x0, dtype=float).reshape(-1)
        if start.size != n:
            raise PracmaError("Argument 'x0' must have the length 'n=ncol(A)=nrow(A).")
    method = match_arg(method, ["Gauss-Seidel", "Jacobi", "Richardson"])
    if method == "Jacobi":
        lower = np.diag(np.diag(matrix))
        upper = eye(n)
        beta = 1
    elif method == "Gauss-Seidel":
        lower = tril(matrix)
        upper = eye(n)
        beta = 1
    else:
        lower = eye(n)
        upper = lower
        beta = 0
    x = start.reshape(-1, 1)
    right = rhs.reshape(-1, 1)
    residual = right - matrix @ x
    r0 = frobenius(residual)
    err = r0
    iteration = 0
    alpha = 1.0
    while err > tol and iteration < nmax:
        iteration += 1
        z = np.linalg.solve(lower, residual)
        z = np.linalg.solve(upper, z)
        if beta == 0:
            alpha = float(z.T @ residual / (z.T @ matrix @ z))
        x = x + alpha * z
        residual = right - matrix @ x
        err = frobenius(residual) / r0
    return {"x": x.reshape(-1), "iter": np.array([float(iteration)]), "method": method}


def _givapp(c, s, v_in, k):
    rotated = np.array(v_in, dtype=complex if np.iscomplexobj(v_in) else float, copy=True).reshape(-1)
    for i in range(k):
        w1 = c[i] * rotated[i] - s[i] * rotated[i + 1]
        w2 = s[i] * rotated[i] + np.conj(c[i]) * rotated[i + 1]
        rotated[i : i + 2] = np.array([w1, w2])
    return rotated


def gmres(A, b, x0=None, errtol=1e-6, kmax=None, reorth=1):
    if not is_numeric(A):
        raise PracmaError("is.numeric(A) is not TRUE")
    if not is_numeric(b):
        raise PracmaError("is.numeric(b) is not TRUE")
    if not is_matrix(A):
        raise PracmaError("is.matrix(A) is not TRUE")
    matrix = np.array(A, dtype=float, copy=False)
    rhs = np.array(b, dtype=float).reshape(-1, 1)
    n = rhs.shape[0]
    if matrix.shape[0] != n or matrix.shape[1] != n:
        raise PracmaError("Matrix 'A' must be square and compatible with 'b'.")
    if kmax is None:
        kmax = n + 1
    kmax = int(kmax)
    if x0 is None:
        x0 = np.zeros((n, 1))
    else:
        x0 = np.array(x0, dtype=float).reshape(-1, 1)
    h = zeros(kmax)
    v = zeros(n, kmax)
    c = zeros(kmax + 1, 1)
    s = zeros(kmax + 1, 1)
    x = x0.copy()
    if frobenius(x) != 0:
        r = rhs - matrix @ x
    else:
        r = rhs.copy()
    rho = frobenius(r)
    g = rho * eye(kmax + 1, 1)
    errtol = errtol * frobenius(rhs)
    error = [rho]
    niter = 0
    if rho < errtol:
        return {"x": x, "error": np.array(error), "niter": np.array([float(niter)])}
    v[:, 0] = (r / rho).reshape(-1)
    k = 0
    while rho > errtol and k < kmax:
        k += 1
        v[:, k] = (matrix @ v[:, k - 1 : k]).reshape(-1)
        normav = frobenius(v[:, k])
        for j in range(k):
            h[j, k - 1] = float(np.dot(v[:, j], v[:, k]))
            v[:, k] = v[:, k] - h[j, k - 1] * v[:, j]
        h[k, k - 1] = frobenius(v[:, k])
        normav2 = h[k, k - 1]
        if (reorth == 1 and normav + 0.001 * normav2 == normav) or reorth == 3:
            for j in range(k):
                hr = float(np.dot(v[:, j], v[:, k]))
                h[j, k - 1] = h[j, k - 1] + hr
                v[:, k] = v[:, k] - hr * v[:, j]
            h[k, k - 1] = frobenius(v[:, k])
        if h[k, k - 1] != 0:
            v[:, k] = v[:, k] / h[k, k - 1]
        if k > 1:
            h[:k, k - 1] = _givapp(c[: k - 1, 0], s[: k - 1, 0], h[:k, k - 1], k - 1)
        nu = frobenius(h[k - 1 : k + 1, k - 1])
        if nu != 0:
            c[k - 1, 0] = np.conj(h[k - 1, k - 1] / nu)
            s[k - 1, 0] = -h[k, k - 1] / nu
            h[k - 1, k - 1] = c[k - 1, 0] * h[k - 1, k - 1] - s[k - 1, 0] * h[k, k - 1]
            h[k, k - 1] = 0
            g[k - 1 : k + 1, 0] = _givapp(c[k - 1 : k, 0], s[k - 1 : k, 0], g[k - 1 : k + 1, 0], 1)
        rho = abs(g[k, 0])
        error.append(rho)
    system = h[:k, :k]
    y = np.linalg.lstsq(system, g[:k, 0], rcond=None)[0]
    x = x0 + v[:, :k] @ y.reshape(-1, 1)
    return {"x": x, "error": np.array(error, dtype=float), "niter": np.array([float(k)])}
