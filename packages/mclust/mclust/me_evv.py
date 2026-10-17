"""meEVV: EM for the EVV model, the R function ``meEVV`` of mclust 6.1.3."""

from __future__ import annotations

import numpy as np

from mclust._me_common import (
    DOUBLE_XMAX,
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
    underflow_text,
    vinv_arg,
    z_matrix,
)


def me_evv(data, z, prior=None, control=None, Vinv=None, warn=None, **_ignored):
    """EM for an EVV mixture (equal volume, variable shape and orientation). Returns the R list as a dict."""
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
            "modelName": "EVV",
            "d": p,
            "G": G,
            "scale": np.nan,
            "shape": nan_like(p),
            "orientation": nan_like((p, p, G)),
        }
        parameters = {"pro": nan_like(G), "mean": nan_like((p, G)), "variance": variance, "Vinv": Vinv}
        return build_result("EVV", prior, n, p, G, zz, parameters, control, np.nan, None, text, 9)

    check_z(zz)
    equal_pro, eps, tol, itmax = control_values(control)
    lwork = max(3 * min(n, p) + max(n, p), 5 * min(n, p))
    k = kernels()

    if prior is not None:
        # R computes the prior, then returns the unfitted list with a warning: EVV has no prior.
        prior_params(prior, x, G, "EVV")
        text = "EVV model is not available with prior"
        emit(warn, text)
        unfitted = {
            "x": x,
            "z": zz,
            "n": n,
            "p": p,
            "G": G,
            "mu": nan_like((p, G)),
            "O": nan_like((p, p, G)),
            "shape.o": nan_like((p, p, G)),
            "scale": nan_like(G),
            "shape": nan_like((p, G)),
            "pro": nan_like(K),
            "loglik": np.nan,
            "eqpro": equal_pro,
            "itmax": itmax[0],
            "tol": tol[0],
            "eps": eps,
            "niterout": 0,
            "errout": np.nan,
            "lwork": lwork,
            "info": None,
            "WARNING": text,
            "returnCode": -1,
        }
        return unfitted

    out = k.meevv(
        (
            fflat(x),
            fflat(zz),
            n,
            p,
            G,
            K,
            [0.0] * (p * G),
            [0.0] * (p * p * G),
            [0.0] * (p * p * G),
            [0.0] * G,
            [0.0] * (p * G),
            [0.0] * K,
            vinv_arg(Vinv),
            0.0,
            int(equal_pro),
            itmax[0],
            tol[0],
            eps,
            0,
            0.0,
            lwork,
            0,
        )
    )
    z_out = farr(out[1], (n, K))
    loglik = float(out[13])
    mu = farr(out[6], (p, G))
    scale = float(out[9][0])
    shape = farr(out[10], (p, G))
    O = farr(out[7], (p, p, G)).transpose(1, 0, 2)
    shape_o = farr(out[8], (p, p, G))
    pro = np.asarray(out[11], dtype=float)
    niterout = int(out[18])
    errout = float(out[19])
    lapack = int(out[21])

    # R: any non-finite or over-limit value sets loglik to .Machine$double.xmax
    if (
        not np.isfinite(loglik)
        or scale > XMAX6
        or np.any(shape > XMAX6)
        or np.any(O > XMAX6)
        or np.isnan(scale)
        or np.any(np.isnan(shape))
        or np.any(np.isnan(O))
    ):
        loglik = DOUBLE_XMAX

    warning = None
    code = 0
    if lapack:
        if lapack > 0:
            warning = "LAPACK DGESVD fails to converge"
        else:
            warning = "input error for LAPACK DGESVD"
        emit(warn, warning)
        z_out = nan_like(z_out.shape)
        O = nan_like(O.shape)
        shape = nan_like(shape.shape)
        scale = np.nan
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -9
    elif loglik > XMAX6:
        warning = "singular covariance"
        emit(warn, warning)
        shape = nan_like(shape.shape)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -1
    elif loglik < -XMAX6:
        warning = underflow_text(equal_pro, "a z column sum")
        emit(warn, warning)
        mu = nan_like(mu.shape)
        pro = nan_like(pro.shape)
        z_out = nan_like(z_out.shape)
        loglik = np.nan
        sigma = nan_like((p, p, G))
        code = -2 if equal_pro else -3
    else:
        # R: sigma <- scale * shape.o
        sigma = scale * shape_o
        if niterout >= itmax[0]:
            warning = "iteration limit reached"
            emit(warn, warning)
            niterout = -niterout
            code = 1

    info = {"iterations": niterout, "error": errout}
    variance = {
        "modelName": "EVV",
        "d": p,
        "G": G,
        "sigma": sigma,
        "scale": scale,
        "shape": shape,
        "orientation": O,
    }
    parameters = {"pro": pro, "mean": mu, "variance": variance, "Vinv": Vinv}
    return build_result("EVV", prior, n, p, G, z_out, parameters, control, loglik, info, warning, code)
