"""meVII: EM for the VII model, the R function ``meVII`` of mclust 6.1.3."""

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
    group_count,
    kernels,
    nan_like,
    prior_params,
    resolve_warn,
    scalar,
    underflow_text,
    vinv_arg,
    z_matrix,
)


def me_vii(data, z, prior=None, control=None, Vinv=None, warn=None, **_ignored):
    """EM for a VII mixture (spherical, variable volume). Returns the R list as a dict."""
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
        variance = {"modelName": "VII", "d": p, "G": G, "sigmasq": nan_like(G)}
        parameters = {
            "pro": nan_like(G),
            "mean": nan_like((p, G)),
            "variance": variance,
            "Vinv": Vinv,
        }
        return build_result("VII", prior, n, p, G, zz, parameters, control, np.nan, None, text, 9)

    check_z(zz)
    equal_pro, eps, tol, itmax = control_values(control)
    k = kernels()

    if prior is None:
        out = k.mevii(
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
                [0.0] * G,
                [0.0] * K,
            )
        )
        z_out, its, err, loglik = out[6], out[7], out[8], out[9]
        mu, sigmasq, pro = out[10], out[11], out[12]
    else:
        pp = prior_params(prior, x, G, "VII")
        out = k.meviip(
            (
                int(equal_pro),
                fflat(x),
                n,
                p,
                G,
                vinv_arg(Vinv),
                scalar(pp["shrinkage"]),
                fflat(pp["mean"]),
                scalar(pp["scale"]),
                scalar(pp["dof"]),
                fflat(zz),
                itmax[0],
                tol[0],
                eps,
                [0.0] * (p * G),
                [0.0] * G,
                [0.0] * K,
            )
        )
        z_out, its, err, loglik = out[10], out[11], out[12], out[13]
        mu, sigmasq, pro = out[14], out[15], out[16]

    z_out = farr(z_out, (n, K))
    mu = farr(mu, (p, G))
    sigmasq = np.asarray(sigmasq, dtype=float)
    pro = np.asarray(pro, dtype=float)
    its = int(its)
    err = float(err)
    loglik = float(loglik)

    warning = None
    code = 0
    if loglik > XMAX6 or np.any(sigmasq <= max(eps, 0.0)):
        warning = "sigma-squared falls below threshold"
        emit(warn, warning)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        sigmasq = nan_like(sigmasq.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -1
    elif loglik < -XMAX6:
        warning = underflow_text(equal_pro, "z column sum")
        emit(warn, warning)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        sigmasq = nan_like(sigmasq.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -2 if equal_pro else -3
    else:
        sigma = np.zeros((p, p, G), dtype=float)
        for g in range(G):
            sigma[:, :, g] = np.diag(np.repeat(sigmasq[g], p))
        if its >= itmax[0]:
            warning = "iteration limit reached"
            emit(warn, warning)
            its = -its
            code = 1

    info = {"iterations": its, "error": err}
    variance = {
        "modelName": "VII",
        "d": p,
        "G": G,
        "sigma": sigma,
        "sigmasq": sigmasq,
        "scale": sigmasq,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return build_result("VII", prior, n, p, G, z_out, parameters, control, loglik, info, warning, code)
