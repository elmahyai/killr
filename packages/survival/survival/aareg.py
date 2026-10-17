"""Aalen's additive regression model (survival::aareg)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from survival._coxdetail_core import _coxdetail
from survival._yates_mm import build_terms, model_matrix
from survival.surv import SurvObject, is_Surv
from survival.surv_split import _apply_subset, _as_table
from survival.survobrien import (
    _build_model_frame,
    _column_values,
    _drop_term,
    _eval_expr,
    _factor,
)
from survival.untangle_specials import untangle_specials


def _match_arg(value, choices: list[str]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    hits = [c for c in choices if c == text or c.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ValueError(f"'{text}' is ambiguous")
    raise ValueError(f"'{text}' should be one of {', '.join(choices)}")


def _qr_rank(A: np.ndarray, tol: float) -> int:
    _, r = np.linalg.qr(A, mode="reduced")
    diag = np.abs(np.diag(r))
    if diag.size == 0:
        return 0
    threshold = tol * diag[0]
    return int(np.sum(diag > threshold))


def _qr_coef(A: np.ndarray, y: np.ndarray, tol: float = 1e-7) -> np.ndarray:
    """R qr.coef for one rhs vector or matrix of rhs columns."""
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 1:
        y_arr = y_arr.reshape(-1, 1)
    q, r = np.linalg.qr(A, mode="reduced")
    diag = np.abs(np.diag(r))
    rank = _qr_rank(A, tol)
    if rank == 0:
        return np.full(A.shape[1], np.nan)
    coef = np.linalg.solve(r[:rank, :rank], (q.T @ y_arr)[:rank, :])
    out = np.full((A.shape[1], y_arr.shape[1]), np.nan, dtype=float)
    out[:rank, :] = coef
    if y_arr.shape[1] == 1:
        return out[:, 0]
    return out


def _rowsum(x: np.ndarray, group: np.ndarray, *, reorder: bool = True) -> np.ndarray:
    """R stats::rowsum."""
    x_arr = np.asarray(x, dtype=float)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(-1, 1)
    group = np.asarray(group)
    if reorder:
        levels = np.sort(np.unique(group))
    else:
        seen: list[Any] = []
        for g in group:
            if g not in seen:
                seen.append(g)
        levels = np.asarray(seen)
    out = np.zeros((len(levels), x_arr.shape[1]), dtype=float)
    for i, level in enumerate(levels):
        out[i] = x_arr[group == level].sum(axis=0)
    if out.shape[1] == 1:
        return out[:, 0]
    return out


def _aareg_taper(taper: Any, imat: np.ndarray, nevent: np.ndarray) -> np.ndarray:
    """Running averages of an information matrix (aareg.taper)."""
    nvar = imat.shape[1]
    ntime = imat.shape[0]
    taper_arr = np.asarray(taper, dtype=float).reshape(-1)
    if taper_arr.size == 0 or np.any(taper_arr <= 0):
        raise ValueError("Invalid taper vector")
    ntaper = int(taper_arr.size)
    if ntaper > ntime:
        taper_arr = taper_arr[:ntime]
        ntaper = ntime
    stacked = np.transpose(imat, (1, 2, 0))
    flat = stacked.reshape(nvar * nvar, ntime, order="F")
    flat = flat / nevent.reshape(1, -1)
    if ntaper > 1:
        smoother = np.zeros((ntime, ntime), dtype=float)
        tsum = np.cumsum(taper_arr[::-1])
        for i in range(ntaper):
            idx = np.linspace(ntaper - 1, ntaper - i - 1, i + 1, dtype=int)
            smoother[: i + 1, i] = taper_arr[idx] / tsum[i]
        if ntaper < ntime:
            for i in range(ntaper, ntime):
                smoother[i - ntaper + 1 : i + 1, i] = taper_arr / tsum[ntaper - 1]
        flat = flat @ smoother
    out = flat.reshape(nvar, nvar, ntime, order="F")
    return np.transpose(out, (2, 0, 1))


def _design_matrix(
    terms: dict[str, Any],
    mf_names: list[str],
    mf_cols: list[Any],
) -> tuple[np.ndarray, list[str]]:
    lhs = mf_names[0]
    name_to_col = {name: col for name, col in zip(mf_names, mf_cols)}
    labels = [lab for lab in terms["term.labels"] if not lab.lower().startswith("cluster(")]
    table: dict[str, Any] = {lhs: mf_cols[0]}
    for label in labels:
        if label in name_to_col:
            col = name_to_col[label]
            if is_Surv(col):
                continue
            table[label] = _column_values(col)
    formula = f"{lhs} ~ " + (" + ".join(labels) if labels else "1")
    terms_obj = build_terms(formula, table)
    mm_data = dict(table)
    xmat, names, _assign = model_matrix(terms_obj, mm_data)
    if terms_obj.intercept and xmat.shape[1] > 0:
        xmat = xmat[:, 1:]
        names = names[1:]
    return xmat, names


def _surv_matrix(y: Any) -> np.ndarray:
    if isinstance(y, SurvObject):
        return np.asarray(y.matrix(), dtype=float)
    arr = np.asarray(y, dtype=float)
    if arr.ndim == 1:
        raise ValueError("Response must be a survival object")
    return arr


@dataclass
class AaregResult:
    n: np.ndarray
    times: np.ndarray
    nrisk: np.ndarray
    coefficient: np.ndarray
    test_statistic: np.ndarray
    test_var: np.ndarray
    test: str
    tweight: np.ndarray
    call: dict[str, Any]
    dfbeta: np.ndarray | None = None
    test_var2: np.ndarray | None = None
    weights: np.ndarray | None = None
    na_action: Any = None
    model: Any = None
    x: np.ndarray | None = None
    y: np.ndarray | None = None
    class_: tuple[str, ...] = field(default_factory=lambda: ("aareg",))


def aareg(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action=None,
    qrtol: float = 1e-7,
    nmin=None,
    dfbeta: bool = False,
    taper=1,
    test="aalen",
    cluster=None,
    model: bool = False,
    x: bool = False,
    y: bool = False,
):
    """Fit Aalen's additive regression model."""
    if formula is None:
        raise ValueError("a formula argument is required")
    if data is None:
        raise ValueError("data argument is required")
    test = _match_arg(test, ["aalen", "variance", "nrisk"])

    formula_text = str(formula)
    table = _as_table(data)
    table, _ = _apply_subset(table, subset)

    mf_names, mf_cols, terms = _build_model_frame(
        formula_text, table, subset=None, na_action=na_action
    )

    cluster_info = untangle_specials(terms, "cluster")
    cluster_vars = cluster_info.get("vars") or []
    tcl = terms.get("specials", {}).get("cluster") or []
    if len(cluster_vars) > 1:
        raise ValueError("a formula cannot have multiple cluster terms")
    if len(tcl) > 0:
        factors = terms["factors"]["matrix"]
        if any(factors[row - 1][col - 1] > 1 for row in tcl for col in range(len(terms["term.labels"]))):
            raise ValueError("cluster() cannot be in an interaction")
        if terms["response"] == 0:
            raise ValueError("formula must have a Surv response")
        if cluster is None:
            cluster = _eval_expr(cluster_vars[0], dict(zip(mf_names, mf_cols)))
        else:
            warnings.warn(
                "cluster appears both in a formula and as an argument, formula term ignored",
                stacklevel=2,
            )
        terms = _drop_term(terms, tcl[0])

    strats = terms.get("specials", {}).get("strata") or []
    if len(strats) > 0:
        raise ValueError("Strata terms not allowed")

    Y = _surv_matrix(mf_cols[0])
    if not is_Surv(mf_cols[0]):
        raise ValueError("Response must be a survival object")
    surv_type = mf_cols[0].type if isinstance(mf_cols[0], SurvObject) else "right"
    if surv_type not in ("right", "counting"):
        raise ValueError(f'Aalen model doesn\'t support "{surv_type}" survival data')

    X, xnames = _design_matrix(terms, mf_names, mf_cols)
    nvar = X.shape[1]
    nused = X.shape[0]

    wt = None
    if weights is not None:
        if isinstance(weights, str):
            wt = np.asarray(table[weights], dtype=float)
        else:
            wt = np.asarray(weights, dtype=float)
    if wt is None:
        wt = np.ones(nused, dtype=float)
    else:
        wt = wt[:nused]

    if cluster is not None:
        cl = _factor(cluster)
        cluster_arr = np.array(
            [np.nan if c is None else float(i + 1) for i, c in enumerate(cl.codes)],
            dtype=float,
        )
        dfbeta = True
    elif dfbeta:
        cluster_arr = np.arange(1, nused + 1, dtype=float)
    else:
        cluster_arr = None

    if cluster_arr is not None:
        ncluster = len(np.unique(cluster_arr[~np.isnan(cluster_arr)]))
    else:
        ncluster = nused

    if Y.shape[1] == 2:
        mintime = float(np.min(Y[:, 0]))
        if mintime < 0:
            start = np.full(Y.shape[0], 2 * mintime - 1, dtype=float)
            Y = np.column_stack([start, Y])
        else:
            Y = np.column_stack([np.full(Y.shape[0], -1.0), Y])

    times = Y[:, 1].copy()
    status = Y[:, 2].copy()
    ndeath_max = len(np.unique(times[status == 1]))

    ord_idx = np.lexsort((-status, times))
    times = times[ord_idx]
    status = status[ord_idx]
    wt = wt[ord_idx]
    save_x = X.copy() if x else None
    X = X[ord_idx]
    Y = Y[ord_idx]
    cluster_ord = cluster_arr[ord_idx] if cluster_arr is not None else None

    center = np.mean(X, axis=0)
    strata = np.zeros(nused, dtype=int)
    score = np.ones(nused, dtype=float)

    ff = _coxdetail(
        nused,
        nvar,
        ndeath_max,
        center,
        Y,
        X,
        strata,
        score,
        wt,
        0.0,
        True,
    )
    ndetail = ff["ndeath"]
    riskmat = ff["rmat"][:ndetail].T.astype(float)

    var_raw = ff["var"][:ndetail]
    nevent_slice = ff["event2"][:ndetail]
    dt_var = _aareg_taper(taper, var_raw, nevent_slice)
    dt_means = ff["means"][:ndetail]
    dt_nrisk = ff["nrisk2"][:ndetail]
    dt_nevent = ff["event2"][:ndetail]
    dt_time = Y[ff["index"][:ndetail] - 1, 1]

    if nmin is None:
        nmin = 3 * nvar
    if nvar == 1:
        ndeath = int(np.sum((dt_nrisk >= nmin) & (dt_var.reshape(-1) > 0)))
    else:
        ndeath = int(np.sum(dt_nrisk >= nmin))
        if ndeath > 0:
            while True:
                qrank = _qr_rank(dt_var[ndeath - 1], qrtol)
                if qrank >= nvar:
                    break
                ndeath -= 1
                if ndeath <= 0:
                    break

    if ndeath <= 1:
        raise ValueError("The threshold 'nmin' is too high, no model can be fit")

    dt_time = dt_time[:ndeath]
    dt_means = dt_means[:ndeath]
    dt_var = dt_var[:ndeath]
    dt_nrisk = dt_nrisk[:ndeath]
    dt_nevent = dt_nevent[:ndeath]
    riskmat = riskmat[:, :ndeath]

    index = np.zeros(times.shape[0], dtype=int)
    for i, t in enumerate(times):
        hits = np.where(dt_time == t)[0]
        index[i] = (hits[0] + 1) if hits.size else 0
    index = index * status
    deaths = (status == 1) & (index > 0)
    dindex = (index[deaths] - 1).astype(int)
    nevent = dindex.size

    test_var2 = None
    test_dfbeta = None
    dmat = None

    if dfbeta:
        dmat = np.zeros((ncluster, nvar + 1, ndeath), dtype=float)
        resid = np.zeros((nevent, nused), dtype=float)
        death_rows = np.where(deaths)[0]
        for ev, row in enumerate(death_rows):
            resid[ev, row] = 1.0

    if nvar == 1:
        means_d = dt_means[dindex, 0]
        nrisk_d = dt_nrisk[dindex]
        xx = (X[deaths, 0] - means_d) * wt[deaths]
        v_inverse = 1.0 / dt_var[dindex, 0, 0]
        twt = nrisk_d.reshape(-1, 1) / np.column_stack(
            [1 + means_d**2 * v_inverse, v_inverse]
        )
        coefficient = (v_inverse * xx / nrisk_d).reshape(-1, 1)
        b0 = wt[deaths] / nrisk_d - means_d * coefficient[:, 0]
        if dfbeta:
            xx_r = (X[:, 0].reshape(1, -1) * riskmat[:, dindex]).T
            predicted = coefficient[:, 0].reshape(-1, 1) * xx_r + b0.reshape(-1, 1) * riskmat[:, dindex].T
            resid = resid - predicted
            temp1 = (
                resid
                * (xx_r - means_d.reshape(-1, 1))
                / (nrisk_d.reshape(-1, 1) * dt_var[dindex, 0, 0].reshape(-1, 1))
            ) * wt.reshape(1, -1)
            temp0 = resid * (1.0 / nrisk_d).reshape(-1, 1) * wt.reshape(1, -1) - temp1 * means_d.reshape(-1, 1)
            if test == "nrisk":
                test_dfbeta = np.column_stack(
                    [(temp0 * nrisk_d.reshape(-1, 1)).sum(axis=0), (temp1 * nrisk_d.reshape(-1, 1)).sum(axis=0)]
                )
            else:
                test_dfbeta = np.column_stack(
                    [(temp0 * twt[:, 0].reshape(-1, 1)).sum(axis=0), (temp1 * twt[:, 1].reshape(-1, 1)).sum(axis=0)]
                )
            if nevent > ndeath:
                death_times = times[deaths]
                temp1 = _rowsum(temp1, death_times, reorder=False)
                temp0 = _rowsum(temp0, death_times, reorder=False)
            dmat[:, 0, :] = _rowsum(temp0.T, cluster_ord, reorder=False)
            dmat[:, 1, :] = _rowsum(temp1.T, cluster_ord, reorder=False)
        coefficient = np.column_stack([b0, coefficient[:, 0]])
        if test == "nrisk":
            temp = coefficient * nrisk_d.reshape(-1, 1)
            test_statistic = temp.sum(axis=0)
            test_var = np.zeros((2, 2), dtype=float)
            np.fill_diagonal(test_var, (temp**2).sum(axis=0))
            test_var[0, 1] = test_var[1, 0] = float(np.sum(temp[:, 0] * temp[:, 1]))
        else:
            temp = coefficient * twt
            test_statistic = temp.sum(axis=0)
            test_var = np.zeros((2, 2), dtype=float)
            np.fill_diagonal(test_var, (temp**2).sum(axis=0))
            test_var[0, 1] = test_var[1, 0] = float(np.sum(temp[:, 0] * temp[:, 1]))
    else:
        coefficient = np.zeros((nevent, nvar), dtype=float)
        twt = np.zeros((nevent, nvar + 1), dtype=float)
        means_ev = dt_means[dindex]
        nrisk_d = dt_nrisk[dindex]
        dindex2 = np.where(deaths)[0]
        ybar = wt[deaths] / nrisk_d
        test_var = np.zeros((nvar + 1, nvar + 1), dtype=float)
        if dfbeta:
            test_dfbeta = np.zeros((nused, nvar + 1), dtype=float)
        qri_cache = None
        vmat_cache = None
        last_d = -1
        for i in range(nevent):
            who = riskmat[:, dindex[i]] > 0
            wt_who = wt * who
            xx = who * (X - means_ev[i])
            if i == 0 or dindex[i] != last_d:
                qri_a = dt_var[dindex[i]]
                vmat = _qr_coef(qri_a, np.eye(nvar), tol=qrtol)
                twt[i, 0] = nrisk_d[i] / (1 + means_ev[i] @ vmat @ means_ev[i])
                twt[i, 1:] = nrisk_d[i] / np.diag(vmat)
                qri_cache = qri_a
                vmat_cache = vmat
                last_d = dindex[i]
            else:
                twt[i] = twt[i - 1]
            j = dindex2[i]
            coefficient[i] = _qr_coef(qri_cache, wt_who[j] * xx[j], tol=qrtol) / nrisk_d[i]
            if test == "variance":
                temp = wt_who[j] * xx[j]
                test_var[1:, 1:] += np.outer(temp, temp)
            if dfbeta:
                resid[i] -= ybar[i] + xx @ coefficient[i]
                temp1 = _qr_coef(qri_cache, (resid[i] * wt_who * xx).T, tol=qrtol).T / nrisk_d[i]
                temp0 = resid[i] * wt_who / nrisk_d[i] - temp1 @ means_ev[i]
                if test == "aalen":
                    test_dfbeta += np.column_stack([temp0, temp1]) * twt[i]
                elif test == "nrisk":
                    test_dfbeta += np.column_stack([temp0, temp1]) * nrisk_d[i]
                else:
                    test_dfbeta[:, 1:] += np.outer(resid[i], wt_who * xx)
                    test_dfbeta[:, 0] += temp0 * twt[i, 0]
                dmat[:, 1:, dindex[i]] += _rowsum(temp1, cluster_ord, reorder=False)
                dmat[:, 0, dindex[i]] += _rowsum(temp0, cluster_ord, reorder=False)
        temp = (means_ev * coefficient).sum(axis=1)
        b0 = wt[deaths] / nrisk_d - temp
        coefficient = np.column_stack([b0, coefficient])
        if test == "aalen":
            temp = twt * coefficient
            test_statistic = temp.sum(axis=0)
            test_var = temp.T @ temp
        elif test == "nrisk":
            temp = coefficient * nrisk_d.reshape(-1, 1)
            test_statistic = temp.sum(axis=0)
            test_var = temp.T @ temp
        else:
            xx_ev = wt[deaths].reshape(-1, 1) * (X[deaths] - means_ev)
            test_statistic = np.concatenate([[0.0], xx_ev.sum(axis=0)])

    if dfbeta and test_dfbeta is not None:
        cl = cluster_ord if cluster_ord is not None else np.arange(1, nused + 1)
        temp = _rowsum(test_dfbeta, cl, reorder=False)
        test_var2 = temp.T @ temp

    test_statistic = np.asarray(test_statistic, dtype=float)
    test_statistic = test_statistic.reshape(-1)

    ans = AaregResult(
        n=np.array([nused, ndeath, len(dt_time)], dtype=int),
        times=times[deaths],
        nrisk=dt_nrisk[dindex],
        coefficient=coefficient,
        test_statistic=test_statistic,
        test_var=test_var,
        test=test,
        tweight=twt,
        call={"function": "aareg", "formula": formula_text},
    )
    if dfbeta:
        ans.dfbeta = dmat
        ans.test_var2 = test_var2
    if not np.all(wt == 1):
        ans.weights = wt
    if model:
        ans.model = dict(zip(mf_names, mf_cols))
    else:
        if x:
            ans.x = save_x
        if y:
            ans.y = Y
    ans.class_ = ("aareg",)
    return ans
