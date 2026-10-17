"""Negative-binomial model for SAGE libraries with Pearson dispersion.

Translated from statmod 1.5.2 ``fitNBP`` in ``R/fitNBP.R``.
"""

from __future__ import annotations

import warnings

import numpy as np


def fit_nbp(y, group=None, lib_size=None, tol=1e-5, maxit=40, verbose=False):
    """Fit a multi-group negative-binomial model with common dispersion."""
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y.reshape(1, -1)
    elif y.ndim != 2:
        raise ValueError("y must be a matrix")

    ngenes, nlib = y.shape

    if group is None:
        group_arr = np.ones(nlib, dtype=float)
    else:
        group_arr = np.asarray(group).reshape(-1)
        if group_arr.size != nlib:
            raise ValueError("length(group) must agree with ncol(y)")

    levels = np.unique(group_arr)
    levels.sort()
    ngroups = levels.size
    res_df = nlib - ngroups

    ind = np.zeros((nlib, ngroups), dtype=bool)
    for i, level in enumerate(levels):
        ind[:, i] = group_arr == level

    if lib_size is None:
        lib_size_arr = np.sum(y, axis=0, dtype=float)
    else:
        lib_size_arr = np.asarray(lib_size, dtype=float).reshape(-1)
        if lib_size_arr.size != nlib:
            raise ValueError("length(lib.size) must agree with ncol(y)")

    offset = np.log(lib_size_arr)
    mu = np.maximum(y, 0.5)
    phi = 0.0
    w = mu.copy()
    z = w * (np.log(mu) - offset[np.newaxis, :])
    beta = np.zeros((ngenes, ngroups), dtype=float)
    eta = np.broadcast_to(offset, (ngenes, nlib)).copy()
    for i in range(ngroups):
        cols = ind[:, i]
        w_sum = np.sum(w[:, cols], axis=1)
        beta[:, i] = np.sum(z[:, cols], axis=1) / w_sum
        eta[:, cols] = eta[:, cols] + beta[:, i][:, np.newaxis]
    if verbose:
        print("mean coef", np.mean(beta, axis=0))
    mu = np.exp(eta)

    low = 0.0
    iter_count = 0
    while True:
        iter_count += 1
        if iter_count > maxit:
            warnings.warn("maxit exceeded", RuntimeWarning, stacklevel=2)
            break

        e2 = (y - mu) ** 2
        dV = mu * mu

        inneriter = 0
        while True:
            inneriter += 1
            if inneriter > 10:
                raise RuntimeError("problem with inner iteration")
            v = mu * (1.0 + phi * mu)
            x2 = np.sum(e2 / v) / res_df - ngenes
            if x2 >= 0.0:
                low = phi
                break
            if phi == 0.0:
                break
            if inneriter > 4:
                phi = 0.9 * phi
            else:
                phi = (low + phi) / 2.0
            if verbose:
                print("mean disp", phi)

        if x2 < 0.0:
            break

        dx2 = np.sum(e2 / v / v * dV) / res_df
        step_phi = x2 / max(dx2, 1e-6)
        phi = phi + step_phi
        conv_crit = step_phi / (phi + 1.0)
        if verbose:
            print("Conv criterion", conv_crit)
        if conv_crit < tol:
            break

        w = mu / (1.0 + phi * mu)
        z = (y - mu) / v * mu
        eta = np.broadcast_to(offset, (ngenes, nlib)).copy()
        for i in range(ngroups):
            cols = ind[:, i]
            w_sum = np.sum(w[:, cols], axis=1)
            beta[:, i] = beta[:, i] + np.sum(z[:, cols], axis=1) / w_sum
            eta[:, cols] = eta[:, cols] + beta[:, i][:, np.newaxis]
        if verbose:
            print("mean coef", np.mean(beta, axis=0))
            print("disp", phi)
        mu = np.exp(eta)

    return {
        "coefficients": np.array(beta, dtype=float, copy=False),
        "fitted_values": np.array(mu, dtype=float, copy=False),
        "dispersion": float(phi),
    }
