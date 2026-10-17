"""meVVV: EM for the VVV model, the R function ``meVVV`` of mclust 6.1.3."""

from __future__ import annotations

import numpy as np

from mclust._me_common import (
    XMAX6,
    build_result,
    check_z,
    control_values,
    data_matrix,
    default_control,
    emit,
    farr,
    fflat,
    fortran_uncholf,
    group_count,
    kernels,
    nan_like,
    prior_params,
    r_chol,
    resolve_warn,
    scalar,
    underflow_text,
    vinv_arg,
    z_matrix,
)


def me_vvv(data, z, prior=None, control=None, Vinv=None, warn=None, **_ignored):
    """EM for a general VVV mixture (unconstrained covariance). Returns the R list as a dict."""
    control = default_control(control)
    warn = resolve_warn(warn)
    x = data_matrix(data)
    n, p = x.shape
    zz = z_matrix(z, n, "data and z should have the same row dimension")
    K = zz.shape[1]
    G, Vinv = group_count(K, Vinv, x)

    if np.all(np.isnan(zz)):
        text = "z is missing"
        emit(warn, text)
        variance = {
            "modelName": "VVV",
            "d": p,
            "G": G,
            "sigma": nan_like((p, p, G)),
            "cholsigma": nan_like((p, p, G)),
        }
        parameters = {"pro": nan_like(G), "mean": nan_like((p, G)), "variance": variance, "Vinv": Vinv}
        return build_result("VVV", prior, n, p, G, zz, parameters, control, np.nan, None, text, 9)

    check_z(zz)
    equal_pro, eps, tol, itmax = control_values(control)
    k = kernels()

    if prior is None:
        out = k.mevvv(
            (
                int(equal_pro),
                fflat(x),
                n,
                p,
                G,
                vinv_arg(Vinv),
                fflat(zz),
                itmax[0],
                tol[0],
                eps,
                [0.0] * (p * G),
                [0.0] * (p * p * G),
                [0.0] * K,
                [0.0] * p,
                [0.0] * (p * p),
            )
        )
        z_out, its, err, loglik = out[6], out[7], out[8], out[9]
        mu, chol_flat, pro = out[10], out[11], out[12]
    else:
        pp = prior_params(prior, x, G, "VVV")
        scale_prior = np.asarray(pp["scale"], dtype=float).reshape(p, p)
        pscale = r_chol(scale_prior) if np.any(scale_prior != 0) else scale_prior
        out = k.mevvvp(
            (
                int(equal_pro),
                fflat(x),
                n,
                p,
                G,
                vinv_arg(Vinv),
                scalar(pp["shrinkage"]),
                fflat(pp["mean"]),
                fflat(pscale),
                scalar(pp["dof"]),
                fflat(zz),
                itmax[0],
                tol[0],
                eps,
                [0.0] * (p * G),
                [0.0] * (p * p * G),
                [0.0] * K,
                [0.0] * p,
                [0.0] * (p * p),
            )
        )
        z_out, its, err, loglik = out[10], out[11], out[12], out[13]
        mu, chol_flat, pro = out[14], out[15], out[16]

    z_out = farr(z_out, (n, K))
    mu = farr(mu, (p, G))
    cholsigma = farr(chol_flat, (p, p, G))
    pro = np.asarray(pro, dtype=float)
    its = int(its)
    err = float(err)
    loglik = float(loglik)

    warning = None
    code = 0
    if loglik > XMAX6:
        warning = "singular covariance"
        emit(warn, warning)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -1
    elif loglik < -XMAX6:
        warning = underflow_text(equal_pro, "z column sum")
        emit(warn, warning)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -2 if equal_pro else -3
    else:
        # R: sigma <- array(apply(cholsigma, 3, unchol, upper = TRUE), c(p, p, G))
        sigma = np.zeros((p, p, G), dtype=float)
        for g in range(G):
            sigma[:, :, g] = fortran_uncholf(True, cholsigma[:, :, g])
        if its >= itmax[0]:
            warning = "iteration limit reached"
            emit(warn, warning)
            its = -its
            code = 1

    info = {"iterations": its, "error": abs(err)}
    variance = {"modelName": "VVV", "d": p, "G": G, "sigma": sigma, "cholsigma": cholsigma}
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return build_result("VVV", prior, n, p, G, z_out, parameters, control, loglik, info, warning, code)
