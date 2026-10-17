"""meVEI: EM for the VEI model, the R function ``meVEI`` of mclust 6.1.3."""

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
    unpack_inner,
    vinv_arg,
    z_matrix,
)


def me_vei(data, z, prior=None, control=None, Vinv=None, warn=None, **_ignored):
    """EM for a VEI mixture (equal shape, variable volume, diagonal). Returns the R list as a dict."""
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
        variance = {"modelName": "VEI", "d": p, "G": G, "scale": nan_like(G), "shape": nan_like(p)}
        parameters = {
            "pro": nan_like(G),
            "mean": nan_like((p, G)),
            "variance": variance,
            "Vinv": Vinv,
        }
        return build_result("VEI", prior, n, p, G, zz, parameters, control, np.nan, None, text, 9)

    check_z(zz)
    equal_pro, eps, tol, itmax = control_values(control)
    k = kernels()

    if prior is None:
        out = k.mevei(
            (
                int(equal_pro),
                fflat(x),
                n,
                p,
                G,
                vinv_arg(Vinv),
                fflat(zz),
                itmax,
                tol,
                eps,
                [0.0] * (p * G),
                [0.0] * G,
                [0.0] * p,
                [0.0] * K,
                [0.0] * G,
                [0.0] * p,
                [0.0] * (p * G),
            )
        )
        z_out, its_out, tol_out, loglik = out[6], out[7], out[8], out[9]
        mu, scale, shape, pro = out[10], out[11], out[12], out[13]
    else:
        pp = prior_params(prior, x, G, "VEI")
        out = k.meveip(
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
                itmax,
                tol,
                eps,
                [0.0] * (p * G),
                [0.0] * G,
                [0.0] * p,
                [0.0] * K,
                [0.0] * G,
                [0.0] * p,
                [0.0] * (p * G),
            )
        )
        z_out, its_out, tol_out, loglik = out[10], out[11], out[12], out[13]
        mu, scale, shape, pro = out[14], out[15], out[16], out[17]

    its, inner, err, inerr = unpack_inner(its_out, tol_out)
    z_out = farr(z_out, (n, K))
    mu = farr(mu, (p, G))
    scale = np.asarray(scale, dtype=float)
    shape = np.asarray(shape, dtype=float)
    pro = np.asarray(pro, dtype=float)
    loglik = float(loglik)

    warning = None
    code = 0
    if loglik > XMAX6:
        warning = "singular covariance"
        emit(warn, warning)
        sigma = nan_like((p, p, G))
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        shape = nan_like(shape.shape)
        loglik = np.nan
        code = -1
    elif loglik < -XMAX6:
        warning = underflow_text(equal_pro, "z column sum")
        emit(warn, warning)
        sigma = nan_like((p, p, G))
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        shape = nan_like(shape.shape)
        loglik = np.nan
        code = -2 if equal_pro else -3
    else:
        sigma = np.zeros((p, p, G), dtype=float)
        for g in range(G):
            sigma[:, :, g] = np.diag(scale[g] * shape)
        if inner >= itmax[1]:
            warning = "inner iteration limit reached"
            emit(warn, warning)
            inner = -inner
            code = 2
        elif its >= itmax[0]:
            warning = "iteration limit reached"
            emit(warn, warning)
            its = -its
            code = 1

    info = {"iterations": its, "error": err, "inner": {"iterations": inner, "error": inerr}}
    variance = {"modelName": "VEI", "d": p, "G": G, "sigma": sigma, "scale": scale, "shape": shape}
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return build_result("VEI", prior, n, p, G, z_out, parameters, control, loglik, info, warning, code)
