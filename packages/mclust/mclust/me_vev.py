"""meVEV: EM for the VEV model, the R function ``meVEV`` of mclust 6.1.3."""

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
    fortran_shapeo,
    group_count,
    kernels,
    nan_like,
    prior_params,
    r_chol,
    resolve_warn,
    scalar,
    underflow_text,
    unpack_inner,
    vinv_arg,
    z_matrix,
)


def me_vev(data, z, prior=None, control=None, Vinv=None, warn=None, **_ignored):
    """EM for a VEV mixture (equal shape, variable volume and orientation). Returns the R list as a dict."""
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
            "modelName": "VEV",
            "d": p,
            "G": G,
            "scale": nan_like(G),
            "shape": nan_like(p),
            "orientation": nan_like((p, p, G)),
        }
        parameters = {"pro": nan_like(G), "mean": nan_like((p, G)), "variance": variance}
        return build_result("VEV", prior, n, p, G, zz, parameters, control, np.nan, None, text, 9)

    check_z(zz)
    equal_pro, eps, tol, itmax = control_values(control)
    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p), p + G)
    k = kernels()

    if prior is None:
        out = k.mevev(
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
                lwork,
                [0.0] * (p * G),
                [0.0] * G,
                [0.0] * p,
                [0.0] * (p * p * G),
                [0.0] * K,
                [0.0] * lwork,
                [0.0] * p,
            )
        )
        z_out, its_out, tol_out, loglik, lapack = out[6], out[7], out[8], out[9], out[10]
        mu, scale, shape, o_flat, pro = out[11], out[12], out[13], out[14], out[15]
    else:
        pp = prior_params(prior, x, G, "VEV")
        scale_prior = np.asarray(pp["scale"], dtype=float).reshape(p, p)
        pscale = r_chol(scale_prior) if np.any(scale_prior != 0) else scale_prior
        out = k.mevevp(
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
                itmax,
                tol,
                eps,
                lwork,
                [0.0] * (p * G),
                [0.0] * G,
                [0.0] * p,
                [0.0] * (p * p * G),
                [0.0] * K,
                [0.0] * lwork,
                [0.0] * p,
            )
        )
        z_out, its_out, tol_out, loglik, lapack = out[10], out[11], out[12], out[13], out[14]
        mu, scale, shape, o_flat, pro = out[15], out[16], out[17], out[18], out[19]

    its, inner, err, inerr = unpack_inner(its_out, tol_out)
    z_out = farr(z_out, (n, K))
    mu = farr(mu, (p, G))
    scale = np.asarray(scale, dtype=float)
    shape = np.asarray(shape, dtype=float)
    pro = np.asarray(pro, dtype=float)
    # R: O <- aperm(array(temp[[9]], c(p, p, G)), c(2, 1, 3))
    O = farr(o_flat, (p, p, G)).transpose(1, 0, 2)
    loglik = float(loglik)
    lapack = int(lapack)

    warning = None
    code = 0
    if lapack:
        if lapack > 0:
            warning = "LAPACK DGESVD fails to converge"
        else:
            warning = "input error for LAPACK DGESVD"
        emit(warn, warning)
        O = nan_like(O.shape)
        shape = nan_like(shape.shape)
        scale = nan_like(scale.shape)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -9
    elif loglik > XMAX6:
        warning = "singular covariance"
        emit(warn, warning)
        O = nan_like(O.shape)
        shape = nan_like(shape.shape)
        scale = nan_like(scale.shape)
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
        # R: sigma <- shapeO(shape, O, transpose = FALSE), then sweep(sigma, 3, scale, "*")
        sigma = fortran_shapeo(shape, O)
        for g in range(G):
            sigma[:, :, g] *= scale[g]
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
    variance = {
        "modelName": "VEV",
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
        "orientation": O,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return build_result("VEV", prior, n, p, G, z_out, parameters, control, loglik, info, warning, code)
