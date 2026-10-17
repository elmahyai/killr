"""meV: univariate EM for the V model, the R function ``meV`` of mclust 6.1.3."""

from __future__ import annotations

import numpy as np

from mclust._me_common import (
    XMAX6,
    build_result,
    check_z,
    control_values,
    data_vector,
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


def me_v(data, z, prior=None, control=None, Vinv=None, warn=None, **_ignored):
    """EM for a one-dimensional variable-variance mixture. Returns the R list as a dict."""
    control = default_control(control)
    warn = resolve_warn(warn)
    x = data_vector(data)
    n = x.size
    zz = z_matrix(z, n, "row dimension of z should equal length of data")
    K = zz.shape[1]
    G, Vinv = group_count(K, Vinv, x)

    if np.all(np.isnan(zz)):
        text = "z is missing"
        emit(warn, text)
        variance = {"modelName": "V", "d": 1, "G": G, "sigmasq": nan_like(G)}
        parameters = {"pro": nan_like(G), "mean": nan_like(G), "variance": variance, "Vinv": Vinv}
        return build_result("V", prior, n, 1, G, zz, parameters, control, np.nan, None, text, 9)

    check_z(zz)
    equal_pro, eps, tol, itmax = control_values(control)
    k = kernels()

    if prior is None:
        out = k.me1v(
            (
                int(equal_pro),
                fflat(x),
                n,
                G,
                vinv_arg(Vinv),
                fflat(zz),
                itmax[0],
                tol[0],
                eps,
                [0.0] * G,
                [0.0] * G,
                [0.0] * K,
            )
        )
        z_out, its, err, loglik = out[5], out[6], out[7], out[8]
        mu, sigmasq, pro = out[9], out[10], out[11]
    else:
        pp = prior_params(prior, x, G, "V")
        out = k.me1vp(
            (
                int(equal_pro),
                fflat(x),
                n,
                G,
                vinv_arg(Vinv),
                scalar(pp["shrinkage"]),
                scalar(pp["mean"]),
                scalar(pp["scale"]),
                scalar(pp["dof"]),
                fflat(zz),
                itmax[0],
                tol[0],
                eps,
                [0.0] * G,
                [0.0] * G,
                [0.0] * K,
            )
        )
        z_out, its, err, loglik = out[9], out[10], out[11], out[12]
        mu, sigmasq, pro = out[13], out[14], out[15]

    z_out = farr(z_out, (n, K))
    mu = np.asarray(mu, dtype=float)
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
        code = -1
    elif loglik < -XMAX6:
        warning = underflow_text(equal_pro, "z column sum")
        emit(warn, warning)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        sigmasq = nan_like(sigmasq.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        code = -2 if equal_pro else -3
    elif its >= itmax[0]:
        warning = "iteration limit reached"
        emit(warn, warning)
        its = -its
        code = 1

    variance = {"modelName": "V", "d": 1, "G": G, "sigmasq": sigmasq, "scale": sigmasq}
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    info = {"iterations": its, "error": err}
    return build_result("V", prior, n, 1, G, z_out, parameters, control, loglik, info, warning, code)
