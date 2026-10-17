"""Newton's method for a nonlinear system."""

from __future__ import annotations

import numpy as np

from pracma.num_grad import jacobian


def newtonsys(Ffun, x0, Jfun=None, *args, maxiter=100, tol=float(np.finfo(float).eps) ** 0.5, **kwargs):
    def residual(point):
        return np.asarray(Ffun(point, *args, **kwargs), dtype=float).reshape(-1)

    def derivative(point):
        if Jfun is None:
            return np.asarray(jacobian(lambda z: residual(z), point), dtype=float)
        return np.asarray(Jfun(point, *args, **kwargs), dtype=float)

    def norm(point):
        return float(np.sqrt(np.sum(np.asarray(point, dtype=float) ** 2)))

    niter = 0
    err = tol + 1
    x = np.asarray(x0, dtype=float).reshape(-1)
    while err >= tol and niter < maxiter:
        niter += 1
        value = residual(x)
        slope = derivative(x)
        delta = -np.linalg.solve(slope, value)
        x = x + delta
        err = norm(delta)
    fnorm = norm(residual(x))
    if niter > maxiter and err > tol:
        print(
            "Fails to converge within maximum number of iterations.\n"
            f"The iterate returned has relative residual {fnorm}"
        )
    return {"zero": x, "fnorm": fnorm, "niter": int(niter)}
