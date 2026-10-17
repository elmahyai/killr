"""Cluster bootstrap and jackknife covariances."""

from __future__ import annotations

import numpy as np

from .cluster import _cluster_frame, _fix_psd
from .model import Fit, SandwichError, match_arg

vcovBSenv: dict = {}


def _groups(column) -> list[np.ndarray]:
    order = []
    buckets: dict = {}
    for i, key in enumerate(column.tolist()):
        if key not in buckets:
            order.append(key)
            buckets[key] = []
        buckets[key].append(i)
    return [np.array(buckets[key], dtype=int) for key in order]


def _refit_coef(x: Fit, rows: np.ndarray, weights=None) -> np.ndarray:
    if x.klass[0] == "glm":
        from .model import glm_fit

        design = x.x[rows]
        response = np.asarray(x.y, dtype=float)[rows]
        prior = None if x.prior_weights is None else np.asarray(x.prior_weights, dtype=float)[rows]
        if weights is not None:
            prior = np.asarray(weights, dtype=float) if prior is None else prior * np.asarray(weights, dtype=float)
        offset = None if x.offset is None else np.asarray(x.offset, dtype=float)[rows]
        return glm_fit(design, response, x.coef_names, family=x.family, weights=prior, offset=offset).coefficients
    design = x.x[rows]
    response = x.y[rows] if np.asarray(x.y).ndim == 1 else x.y[rows]
    prior = None if x.prior_weights is None else np.asarray(x.prior_weights, dtype=float)[rows]
    if weights is not None:
        prior = np.asarray(weights, dtype=float) if prior is None else prior * np.asarray(weights, dtype=float)
    offset = None if x.offset is None else np.asarray(x.offset, dtype=float)[rows]
    scale = None if prior is None else np.sqrt(prior)
    target = response if offset is None else response - offset
    if scale is not None:
        design = design * scale[:, None]
        target = target * scale if np.ndim(target) == 1 else target * scale[:, None]
    q, r = np.linalg.qr(design, mode="reduced")
    if np.ndim(target) == 1:
        return np.linalg.solve(r, q.T @ target)
    return np.linalg.solve(r, q.T @ target)


def _aggregate(samples: list[np.ndarray], sign: int, jackknife: bool, center: str, original: np.ndarray, use: str) -> np.ndarray:
    if jackknife:
        cf = np.column_stack(samples)
        R = cf.shape[1]
        location = np.mean(cf, axis=1) if center == "mean" else original
        centered = cf - location[:, None]
        return sign * (R - 1) / R * (centered @ centered.T)
    cf = np.vstack(samples)
    if use == "complete.obs":
        cf = cf[~np.isnan(cf).any(axis=1)]
    covariance = np.cov(cf, rowvar=False, ddof=1)
    return sign * np.atleast_2d(covariance)


def vcovBS_lm(x: Fit, cluster=None, R: int = 250, type="xy", fix: bool = False, use: str = "pairwise.complete.obs", center: str = "mean", generator: np.random.Generator | None = None, **_kwargs) -> np.ndarray:
    original = np.asarray(x.coefficients, dtype=float).ravel()
    k = len(original)
    n = x.nobs
    groups = _cluster_frame(x, cluster, n)
    p = groups.shape[1]
    from .cluster import combn

    if p > 1:
        patterns = []
        for size in range(1, p + 1):
            patterns.extend(combn(range(p), size))
        signs = [(-1) ** (len(pattern) + 1) for pattern in patterns]
        pasted = []
        for pattern in patterns[p:]:
            pasted.append(np.array(["_".join(str(item) for item in row) for row in groups[:, list(pattern)]]))
        groups = np.column_stack([groups, *pasted]) if pasted else groups
    else:
        patterns = [(0,)]
        signs = [1]
    if isinstance(type, str):
        type = match_arg(type.lower().replace("wild-", ""), ["xy", "jackknife", "fractional", "residual", "wild", "webb", "rademacher", "mammen", "norm", "user"])
        if type == "wild":
            type = "rademacher"
    rng = generator or np.random.default_rng()
    value = np.zeros((k, k))
    y = np.asarray(x.y, dtype=float).ravel()
    fitted = np.asarray(x.fitted, dtype=float).ravel()
    resid = np.asarray(x.residuals, dtype=float).ravel()
    for i in range(len(patterns)):
        bundles = _groups(groups[:, i])
        replicates = len(bundles) if type == "jackknife" else R
        samples = []
        for j in range(replicates):
            if type == "jackknife":
                rows = np.concatenate([bundle for t, bundle in enumerate(bundles) if t != j])
                samples.append(_refit_coef(x, rows))
            elif type == "xy":
                draw = rng.integers(0, len(bundles), len(bundles))
                rows = np.concatenate([bundles[t] for t in draw])
                samples.append(_refit_coef(x, rows))
            elif type == "residual":
                draw = rng.integers(0, len(bundles), len(bundles))
                rows = np.concatenate([bundles[t] for t in draw])
                yboot = fitted + resid[rows]
                samples.append(_refit_coef_response(x, yboot))
            else:
                raise SandwichError(f"bootstrap type '{type}' is not available")
        value = value + _aggregate(samples, signs[i], type == "jackknife", center, original, use)
    if fix and np.any(np.linalg.eigvalsh(value) < 0):
        value = _fix_psd(value)
    return value


def _refit_coef_response(x: Fit, yboot: np.ndarray) -> np.ndarray:
    design = x.x
    prior = None if x.prior_weights is None else np.asarray(x.prior_weights, dtype=float)
    offset = None if x.offset is None else np.asarray(x.offset, dtype=float)
    target = yboot if offset is None else yboot - offset
    if prior is not None:
        scale = np.sqrt(prior)
        design = design * scale[:, None]
        target = target * scale
    q, r = np.linalg.qr(design, mode="reduced")
    return np.linalg.solve(r, q.T @ target)


def vcovBS_default(x: Fit, cluster=None, R: int = 250, start=False, type="xy", fix: bool = False, use: str = "pairwise.complete.obs", center: str = "mean", **kwargs) -> np.ndarray:
    vcovBSenv[".vcovBSstart"] = np.asarray(x.coefficients, dtype=float).ravel() if start is True else None
    try:
        return vcovBS_lm(x, cluster=cluster, R=R, type=type, fix=fix, use=use, center=center, **kwargs)
    finally:
        vcovBSenv.pop(".vcovBSstart", None)


def vcovBS(x: Fit, cluster=None, R: int = 250, type="xy", fix: bool = False, **kwargs) -> np.ndarray:
    if x.klass[0] in {"lm", "glm", "mlm"}:
        return vcovBS_lm(x, cluster=cluster, R=R, type=type, fix=fix, **kwargs)
    return vcovBS_default(x, cluster=cluster, R=R, type=type, fix=fix, **kwargs)


def vcovJK(x: Fit, cluster=None, center: str = "mean", **kwargs) -> np.ndarray:
    center = match_arg(center, ["mean", "estimate"])
    return vcovBS(x, cluster=cluster, center=center, type="jackknife", **kwargs)
