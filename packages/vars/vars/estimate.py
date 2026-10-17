"""VAR estimation and lag selection from vars 1.6-1."""

import math

import numpy as np


class VARResult:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        return f"VARResult(p={self.p}, K={self.K}, type={self.type!r})"


def _as_matrix(y):
    data = np.asarray(y, dtype=float)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    names = getattr(y, "columns", None)
    if names is None:
        names = [f"y{i + 1}" for i in range(data.shape[1])]
    else:
        names = [str(name) for name in list(names)]
    return data, names


def _match(value, choices):
    if value is None:
        return choices[0]
    text = str(value)
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) != 1:
        raise ValueError(f"{value!r} does not match one of {choices}")
    return hits[0]


def _embed(y, dimension):
    rows = y.shape[0] - dimension + 1
    width = y.shape[1]
    out = np.empty((rows, dimension * width))
    for lag in range(dimension):
        out[:, lag * width:(lag + 1) * width] = y[(dimension - 1 - lag):(y.shape[0] - lag)]
    return out


def _lstsq(design, response):
    coef, _residuals, _rank, _sv = np.linalg.lstsq(design, response, rcond=None)
    if response.ndim == 1:
        coef = coef.reshape(-1)
        fitted = design @ coef
    else:
        fitted = design @ coef
    resid = response - fitted
    return coef, resid, fitted


def _seasonal(season, n_rows):
    season = abs(int(season))
    dum = (np.eye(season) - 1.0 / season)[:, :-1]
    repeats = int(math.ceil(n_rows / season))
    return np.vstack([dum] * repeats)[:n_rows]


def VARselect(y, lag_max=10, type="const", season=None, exogen=None):
    data, _names = _as_matrix(y)
    if np.isnan(data).any():
        raise ValueError("NAs in y.")
    k = data.shape[1]
    lag_max = abs(int(lag_max))
    type = _match(type, ("const", "trend", "both", "none"))
    lagged = _embed(data, lag_max + 1)[:, k:]
    endog = data[lag_max:]
    sample = lagged.shape[0]
    if type == "const":
        rhs = np.ones((sample, 1))
    elif type == "trend":
        rhs = np.arange(lag_max + 1, lag_max + 1 + sample, dtype=float).reshape(-1, 1)
    elif type == "both":
        rhs = np.column_stack([
            np.ones(sample),
            np.arange(lag_max + 1, lag_max + 1 + sample, dtype=float),
        ])
    else:
        rhs = None
    if season is not None:
        dums = _seasonal(season, sample)
        rhs = dums if rhs is None else np.column_stack([rhs, dums])
    if exogen is not None:
        exo, _ = _as_matrix(exogen)
        if exo.shape[0] != data.shape[0]:
            raise ValueError("Different row size of y and exogen.")
        block = exo[lag_max:]
        rhs = block if rhs is None else np.column_stack([rhs, block])
    detint = 0 if rhs is None else rhs.shape[1]
    criteria = np.empty((4, lag_max))
    idx = np.arange(k, k * lag_max + 1, k)
    for i in range(1, lag_max + 1):
        design = lagged[:, : idx[i - 1]]
        if rhs is not None:
            design = np.column_stack([design, rhs])
        _coef, resid, _fit = _lstsq(design, endog)
        sigma_det = np.linalg.det(resid.T @ resid / sample)
        penalty = i * k ** 2 + k * detint
        criteria[0, i - 1] = math.log(sigma_det) + (2 / sample) * penalty
        criteria[1, i - 1] = math.log(sigma_det) + (2 * math.log(math.log(sample)) / sample) * penalty
        criteria[2, i - 1] = math.log(sigma_det) + (math.log(sample) / sample) * penalty
        nstar = design.shape[1]
        criteria[3, i - 1] = ((sample + nstar) / (sample - nstar)) ** k * sigma_det
    selection = np.argmin(criteria, axis=1) + 1
    return {"selection": selection, "criteria": criteria}


def VAR(y, p=1, type="const", season=None, exogen=None, lag_max=None, ic="AIC"):
    data, names = _as_matrix(y)
    if np.isnan(data).any():
        raise ValueError("NAs in y.")
    if data.shape[1] < 2:
        raise ValueError("The matrix y should contain at least two variables.")
    type = _match(type, ("const", "trend", "both", "none"))
    if lag_max is not None:
        ic = _match(ic, ("AIC", "HQ", "SC", "FPE"))
        picked = VARselect(data, lag_max=lag_max, type=type, season=season, exogen=exogen)["selection"]
        p = int(picked[{"AIC": 0, "HQ": 1, "SC": 2, "FPE": 3}[ic]])
    p = int(p)
    obs = data.shape[0]
    k = data.shape[1]
    sample = obs - p
    ylags = _embed(data, p + 1)[:, k:]
    yend = data[p:]
    if type == "const":
        rhs = np.column_stack([ylags, np.ones(sample)])
        rhs_names = [f"{name}.l{lag}" for lag in range(1, p + 1) for name in names] + ["const"]
    elif type == "trend":
        rhs = np.column_stack([ylags, np.arange(p + 1, p + 1 + sample, dtype=float)])
        rhs_names = [f"{name}.l{lag}" for lag in range(1, p + 1) for name in names] + ["trend"]
    elif type == "both":
        rhs = np.column_stack([
            ylags, np.ones(sample), np.arange(p + 1, p + 1 + sample, dtype=float),
        ])
        rhs_names = [f"{name}.l{lag}" for lag in range(1, p + 1) for name in names] + ["const", "trend"]
    else:
        rhs = ylags
        rhs_names = [f"{name}.l{lag}" for lag in range(1, p + 1) for name in names]
    if season is not None:
        dums = _seasonal(season, obs)[p:]
        rhs = np.column_stack([rhs, dums])
        rhs_names = rhs_names + [f"sd{i}" for i in range(1, dums.shape[1] + 1)]
    if exogen is not None:
        exo, exo_names = _as_matrix(exogen)
        if exo.shape[0] != data.shape[0]:
            raise ValueError("Different row size of y and exogen.")
        rhs = np.column_stack([rhs, exo[p:]])
        rhs_names = rhs_names + exo_names
    equations = {}
    coefficients = []
    residuals = []
    for i, name in enumerate(names):
        coef, resid, fitted = _lstsq(rhs, yend[:, i])
        df_resid = sample - rhs.shape[1]
        equations[name] = {
            "coefficients": coef,
            "residuals": resid,
            "fitted": fitted,
            "df_residual": df_resid,
            "names": rhs_names,
        }
        coefficients.append(coef)
        residuals.append(resid)
    datamat = np.column_stack([yend, rhs])
    return VARResult(
        varresult=equations,
        datamat=datamat,
        datamat_names=names + rhs_names,
        y=data,
        names=names,
        rhs_names=rhs_names,
        type=type,
        p=p,
        K=k,
        obs=sample,
        totobs=sample + p,
        restrictions=None,
        coefficients=np.vstack(coefficients),
        residuals=np.column_stack(residuals),
    )


def residuals(x):
    return x.residuals


def Bcoef(x):
    return x.coefficients.copy()


def B(x):
    return Bcoef(x)


def Acoef(x):
    k = x.K
    p = x.p
    block = Bcoef(x)[:, : k * p]
    lags = []
    for i in range(p):
        lags.append(block[:, i * k:(i + 1) * k].copy())
    return lags


def A(x):
    return Acoef(x)


def roots(x, modulus=True):
    k = x.K
    p = x.p
    companion = np.zeros((k * p, k * p))
    stacked = np.hstack(Acoef(x))
    companion[:k, :] = stacked
    if p > 1:
        companion[k:, : k * (p - 1)] = np.eye(k * (p - 1))
    values = np.linalg.eigvals(companion)
    if modulus:
        return np.abs(values)
    return values


def logLik(x):
    obs = x.obs
    k = x.K
    resids = residuals(x)
    sigma = resids.T @ resids / obs
    sign, logdet = np.linalg.slogdet(sigma)
    if sign <= 0:
        logdet = math.inf
    quad = np.sum(np.diag(resids @ np.linalg.solve(sigma, resids.T)))
    value = -(obs * k / 2) * math.log(2 * math.pi) - (obs / 2) * logdet - 0.5 * quad
    df = int(np.sum([eq["coefficients"].size for eq in x.varresult.values()]))
    return value, df, obs
