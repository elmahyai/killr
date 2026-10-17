"""Structural VAR by scoring or by direct likelihood."""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2

from .estimate import residuals


def SVAR(x, estmethod="scoring", Amat=None, Bmat=None, start=None, max_iter=100, conv_crit=1e-7, maxls=1.0, lrtest=True):
    estmethod = estmethod if estmethod in ("scoring", "direct") else _only(estmethod, ("scoring", "direct"))
    k = x.K
    if Amat is None and Bmat is None:
        raise ValueError("at least one of Amat or Bmat is required")
    if Amat is None:
        Amat = np.eye(k)
        kind = "B-model"
    elif Bmat is None:
        Bmat = np.eye(k)
        kind = "A-model"
    else:
        Amat = np.array(Amat, dtype=float, copy=True)
        np.fill_diagonal(Amat, 1.0)
        kind = "AB-model"
        free_a = _free_positions(Amat)
        free_b = _free_positions(Bmat)
        if set(free_a) & set(free_b):
            raise ValueError("SVAR not identified: free parameters share a position")
    Amat = np.array(Amat, dtype=float, copy=True)
    Bmat = np.array(Bmat, dtype=float, copy=True)
    if not (np.isnan(Amat).any() or np.isnan(Bmat).any()):
        raise ValueError("Amat or Bmat must contain NA entries to estimate")
    params_a = int(np.isnan(Amat).sum())
    params_b = int(np.isnan(Bmat).sum())
    params = params_a + params_b
    _check_identified(kind, k, params)
    if start is None:
        start = np.full(params, 0.1)
    start = np.asarray(start, dtype=float).reshape(-1)
    if start.size != params:
        raise ValueError("length of start must equal the number of NA entries")
    df = x.varresult[x.names[0]]["df_residual"]
    sigma = residuals(x).T @ residuals(x) / df
    if estmethod == "direct":
        Amat, Bmat, Asigma, Bsigma, opt, iteration = _direct(kind, Amat, Bmat, start, sigma, x.obs, k)
    else:
        Amat, Bmat, Asigma, Bsigma, iteration = _scoring(
            kind, Amat, Bmat, start, sigma, x.obs, k, params_a, params_b, max_iter, conv_crit, maxls,
        )
        opt = None
    Amat, Bmat = _normalize(kind, Amat, Bmat)
    sigma_u = np.linalg.solve(Amat, Bmat) @ Bmat.T @ np.linalg.inv(Amat).T
    over = None
    if lrtest:
        degrees = 0.5 * k * (k + 1) - params
        if degrees != 0:
            statistic = x.obs * (np.log(np.linalg.det(sigma_u)) - np.log(np.linalg.det(sigma)))
            over = {"statistic": float(statistic), "parameter": degrees, "p_value": float(chi2.sf(statistic, degrees))}
    return {
        "A": Amat, "Ase": Asigma, "B": Bmat, "Bse": Bsigma,
        "Sigma_U": sigma_u * 100, "LR": over, "type": kind, "iter": iteration, "opt": opt,
    }


def _only(value, choices):
    hits = [item for item in choices if item.startswith(str(value))]
    if len(hits) != 1:
        raise ValueError(f"{value!r} does not match one of {choices}")
    return hits[0]


def _free_positions(matrix):
    return list(np.flatnonzero(np.isnan(matrix).reshape(-1, order="F")))


def _check_identified(kind, k, params):
    if kind in ("A-model", "B-model"):
        if k ** 2 - params < k * (k - 1) / 2:
            raise ValueError("model is not identified")
    elif 2 * k ** 2 - params < k ** 2 + k * (k - 1) / 2:
        raise ValueError("model is not identified")


def _normalize(kind, amat, bmat):
    if kind == "AB-model":
        for index in np.flatnonzero(np.diag(amat) < 0):
            amat[:, index] *= -1
        for index in np.flatnonzero(np.diag(bmat) < 0):
            bmat[:, index] *= -1
        return amat, bmat
    impact = np.linalg.solve(amat, bmat)
    for index in np.flatnonzero(np.diag(impact) < 0):
        if kind == "B-model":
            bmat[:, index] *= -1
        else:
            amat[:, index] *= -1
    return amat, bmat


def _direct(kind, amat, bmat, start, sigma, obs, k):
    a_index = np.argwhere(np.isnan(amat))
    b_index = np.argwhere(np.isnan(bmat))
    # argwhere is row-major. R which(arr.ind=TRUE) is column-major of NA positions.
    a_index = np.column_stack(np.where(np.isnan(amat).T))[:, ::-1]
    b_index = np.column_stack(np.where(np.isnan(bmat).T))[:, ::-1]

    def objective(coef):
        local_a = amat.copy()
        local_b = bmat.copy()
        if kind == "B-model":
            for row, (i, j) in enumerate(b_index):
                local_b[i, j] = coef[row]
        elif kind == "A-model":
            for row, (i, j) in enumerate(a_index):
                local_a[i, j] = coef[row]
        else:
            n_a = a_index.shape[0]
            for row, (i, j) in enumerate(a_index):
                local_a[i, j] = coef[row]
            for row, (i, j) in enumerate(b_index):
                local_b[i, j] = coef[n_a + row]
        sign, logdet_a = np.linalg.slogdet(local_a)
        _sign_b, logdet_b = np.linalg.slogdet(local_b)
        resolved = np.linalg.solve(local_b.T, local_a)
        quad = np.trace(resolved.T @ resolved @ sigma)
        log_l = -(k * obs / 2) * np.log(2 * np.pi) + obs * logdet_a - obs * logdet_b - obs / 2 * quad
        return -log_l

    opt = minimize(objective, start, method="Nelder-Mead")
    coef = opt.x
    hessian = None
    if kind == "B-model":
        for row, (i, j) in enumerate(b_index):
            bmat[i, j] = coef[row]
    elif kind == "A-model":
        for row, (i, j) in enumerate(a_index):
            amat[i, j] = coef[row]
    else:
        n_a = a_index.shape[0]
        for row, (i, j) in enumerate(a_index):
            amat[i, j] = coef[row]
        for row, (i, j) in enumerate(b_index):
            bmat[i, j] = coef[n_a + row]
    ase = np.zeros_like(amat)
    bse = np.zeros_like(bmat)
    return amat, bmat, ase, bse, {"par": coef, "value": float(opt.fun)}, int(opt.nfev)


def _scoring(kind, amat, bmat, start, sigma, obs, k, params_a, params_b, max_iter, conv_crit, maxls):
    ksq = k * k
    params = params_a + params_b
    ra = rb = None
    Ra = Rb = None
    if kind == "A-model":
        rb = np.eye(k).reshape(-1, order="F")
        ra, Ra = _selection(amat)
    elif kind == "B-model":
        ra = np.eye(k).reshape(-1, order="F")
        rb, Rb = _selection(bmat)
    else:
        ra, Ra = _selection(amat)
        rb, Rb = _selection(bmat)
    restriction = np.zeros((2 * ksq, params))
    if params_a == 0:
        restriction[ksq:, :] = Rb
    elif params_b == 0:
        restriction[:ksq, :] = Ra
    else:
        restriction[:ksq, :params_a] = Ra
        restriction[ksq:, params_a:] = Rb
    fixed = np.concatenate([ra, rb])
    order = []
    for i in range(k):
        order.extend(range(i, ksq, k))
    commutation = np.eye(ksq)[:, order]
    eye_sq = np.eye(ksq)
    eye = np.eye(k)
    gamma = start.copy()
    iteration = 0
    criterion = conv_crit + 1
    info = None
    while criterion > conv_crit:
        previous = gamma.copy()
        vec = restriction @ gamma + fixed
        amat = vec[:ksq].reshape((k, k), order="F")
        bmat = vec[ksq:].reshape((k, k), order="F")
        binv = np.linalg.inv(bmat)
        btinv = np.linalg.inv(bmat.T)
        binv_a = binv @ amat
        mat1 = np.vstack([np.kron(np.linalg.inv(binv_a), btinv), -np.kron(eye, btinv)])
        mat3 = np.hstack([np.kron(np.linalg.inv(binv_a).T, binv), -np.kron(eye, binv)])
        info_ab = obs * (mat1 @ (eye_sq + commutation) @ mat3)
        info = restriction.T @ info_ab @ restriction
        info_inv = np.linalg.inv(info)
        score_inner = obs * np.linalg.inv(binv_a).T.reshape(-1, order="F") - obs * (np.kron(sigma, eye) @ binv_a.reshape(-1, order="F"))
        score_mat = np.vstack([np.kron(eye, btinv), -np.kron(binv_a, btinv)])
        score = restriction.T @ (score_mat @ score_inner)
        direction = info_inv @ score
        length = np.max(np.abs(direction))
        step = 1.0 if length <= maxls else maxls / length
        gamma = gamma + step * direction
        iteration += 1
        criterion = np.max(np.abs(previous - gamma))
        if iteration >= max_iter:
            break
    reported = iteration - 1
    ab = np.sqrt(np.diag(restriction @ np.linalg.inv(info) @ restriction.T))
    return amat, bmat, ab[:ksq].reshape((k, k), order="F"), ab[ksq:].reshape((k, k), order="F"), reported


def _selection(matrix):
    flat = matrix.reshape(-1, order="F").astype(float)
    pos = np.flatnonzero(np.isnan(flat))
    selector = np.zeros((flat.size, pos.size))
    for column, position in enumerate(pos):
        selector[position, column] = 1
    flat[pos] = 0
    return flat, selector
