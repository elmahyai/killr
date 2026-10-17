"""Linear projection used by BB::spg."""

import numpy as np


def project_linear(par, A, b, meq):
    """Project par onto A x >= b. The first meq rows are equalities."""
    from quadprog import solve_qp

    point = np.asarray(par, dtype=float).reshape(-1).copy()
    matrix = np.asarray(A, dtype=float)
    bound = np.asarray(b, dtype=float).reshape(-1)
    gap = bound - matrix @ point
    if meq > 0 or np.any(gap > 0):
        step = solve_qp(
            np.eye(point.size),
            np.zeros(point.size),
            matrix.T,
            gap,
            meq=meq,
            factorized=True,
        )
        point = point + step["solution"]
    return point
