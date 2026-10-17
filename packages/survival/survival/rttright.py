"""Redistribute-to-the-right weights (survival::rttright)."""

from __future__ import annotations

import re
import warnings
from typing import Any, Mapping

import numpy as np

from survival.fromtimeline import TimelineFrame, _duplicated, _model_extract, _model_response
from survival.strata import StrataFactor, strata as strata_fn
from survival.surv import SurvObject, aeqSurv, is_Surv
from survival.surv_split import _apply_subset, _as_table, _column_len, _parse_surv_lhs
from survival.survcheck import _apply_na_action, _build_response, _survcheck2
from survival.untangle_specials import untangle_specials


def _split_rhs_terms(rhs: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(rhs):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "+" and depth == 0:
            parts.append(rhs[start:i].strip())
            start = i + 1
    parts.append(rhs[start:].strip())
    return [part for part in parts if part]


def _parse_cluster_term(term: str) -> bool:
    return bool(re.match(r"cluster\s*\(", term.strip(), flags=re.IGNORECASE))


def _build_terms(formula_text: str, mf_names: list[str], term_labels: list[str]) -> dict[str, Any]:
    covars = [name for name in term_labels if name in mf_names]
    nrows = len(covars) + 1
    matrix = [[0] * len(covars) for _ in range(nrows)]
    for j, name in enumerate(covars):
        matrix[j + 1][j] = 1
    specials: dict[str, list[int]] = {}
    cluster_terms = [t for t in term_labels if _parse_cluster_term(t)]
    for j, name in enumerate(covars):
        if _parse_cluster_term(name):
            specials.setdefault("cluster", []).append(j + 2)
    return {
        "response": 1,
        "order": [1] * len(covars),
        "factors": {"matrix": matrix, "rownames": [mf_names[0], *covars], "colnames": covars},
        "specials": specials,
        "term.labels": term_labels,
        "offset": None,
    }


def _build_model_frame(
    formula_text: str,
    data: Mapping[str, Any] | TimelineFrame,
    *,
    subset=None,
    weights=None,
    na_action=None,
    id=None,
    istate=None,
) -> TimelineFrame:
    if "~" not in formula_text:
        raise ValueError("a formula argument is required")
    lhs, rhs = formula_text.split("~", 1)
    is_surv2, lhs_names = _parse_surv_lhs(lhs.strip())
    if is_surv2:
        raise ValueError("response must be a Surv object")
    table = _as_table(data)
    table, _ = _apply_subset(table, subset)
    response = _build_response(table, False, lhs_names)
    rhs_terms = _split_rhs_terms(rhs.strip())
    term_names: list[str] = []
    for term in rhs_terms:
        if term == "1":
            continue
        if term == ".":
            used = set(lhs_names)
            term_names.extend(name for name in table if name not in used)
        elif _parse_cluster_term(term):
            term_names.append(term)
        else:
            if term not in table:
                raise ValueError(f"variable {term!r} not found in data")
            term_names.append(term)
    mf_names = [lhs.strip(), *term_names]
    mf_cols: list[Any] = [response]
    for name in term_names:
        if _parse_cluster_term(name):
            continue
        mf_cols.append(table[name])
    specials: dict[str, Any] = {}
    if id is not None:
        if isinstance(id, str):
            if id not in table:
                raise ValueError(f"id variable {id!r} not found in data")
            id_col = table[id]
        else:
            id_col = id
        if _column_len(id_col) != _column_len(mf_cols[0]):
            raise ValueError("wrong length for id")
        mf_names.append("(id)")
        mf_cols.append(id_col)
        specials["id"] = id_col
    if istate is not None:
        if isinstance(istate, str):
            if istate not in table:
                raise ValueError(f"istate variable {istate!r} not found in data")
            istate_col = table[istate]
        else:
            istate_col = istate
        mf_names.append("(istate)")
        mf_cols.append(istate_col)
        specials["istate"] = istate_col
    if weights is not None:
        if isinstance(weights, str):
            if weights not in table:
                raise ValueError(f"weights variable {weights!r} not found in data")
            wt_col = table[weights]
        else:
            wt_col = np.asarray(weights, dtype=float)
        mf_names.append("(weights)")
        mf_cols.append(wt_col)
        specials["weights"] = wt_col
    mf = TimelineFrame(mf_names, mf_cols, specials)
    mf, _ = _apply_na_action(mf, na_action)
    return mf


def _find_interval(values, cuts, *, left_open: bool = False) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    cuts = np.asarray(cuts, dtype=float)
    if left_open:
        index = np.searchsorted(cuts, values, side="left")
    else:
        index = np.searchsorted(cuts, values, side="right")
    out = index.astype(int)
    out[np.isnan(values)] = -1
    return out


def _as_numeric_strata(strata_obj: StrataFactor | Any) -> np.ndarray:
    if isinstance(strata_obj, StrataFactor):
        codes = []
        for code in strata_obj.codes:
            codes.append(1 if code is None else int(code))
        return np.asarray(codes, dtype=int)
    return np.asarray(strata_obj, dtype=int)


def _survfit_km_one(y: np.ndarray, wt: np.ndarray) -> dict[str, np.ndarray]:
    """Kaplan–Meier at event times (censoring distribution for rttright)."""
    n = y.shape[0]
    if y.shape[1] == 2:
        y = np.column_stack([np.zeros(n, dtype=float), y[:, 0], y[:, 1]])
    time1 = y[:, 0]
    time2 = y[:, 1]
    status = y[:, 2]
    position = np.full(n, 3, dtype=int)
    event = status == 1
    utime = np.sort(np.unique(time2[event | (position > 1)]))
    sort2 = np.argsort(time2, kind="mergesort")
    sort1 = np.argsort(time1, kind="mergesort")
    ntime = utime.size
    n1 = 0
    wt1 = 0.0
    person1 = n - 1
    person2 = n - 1
    nmat = np.zeros((ntime, 6), dtype=float)
    for k in range(ntime - 1, -1, -1):
        dt = utime[k]
        n2 = n3 = 0
        wt2 = wt3 = 0.0
        while person2 >= 0:
            i2 = sort2[person2]
            if time2[i2] < dt:
                break
            n1 += 1
            wt1 += wt[i2]
            if status[i2] == 1:
                n2 += 1
                wt2 += wt[i2]
            elif position[i2] & 2:
                n3 += 1
                wt3 += wt[i2]
            person2 -= 1
        while person1 >= 0:
            i1 = sort1[person1]
            if time1[i1] < dt:
                break
            n1 -= 1
            wt1 -= wt[i1]
            person1 -= 1
        nmat[k, :] = (n1, n2, n3, wt1, wt2, wt3)
    km = 1.0
    surv = np.zeros(ntime, dtype=float)
    for i in range(ntime):
        d1 = nmat[i, 4]
        nrisk = nmat[i, 3]
        if nmat[i, 1] > 0 and d1 > 0:
            km *= (nrisk - d1) / nrisk
        surv[i] = km
    return {"time": utime, "n.event": nmat[:, 1], "surv": surv}


def _survfit_km(y: np.ndarray, istrat: np.ndarray, wt: np.ndarray) -> dict[int, dict[str, np.ndarray]]:
    maxstrat = int(np.max(istrat))
    out: dict[int, dict[str, np.ndarray]] = {}
    for i in range(1, maxstrat + 1):
        keep = istrat == i
        if not np.any(keep):
            continue
        out[i] = _survfit_km_one(y[keep], wt[keep])
    return out


def _grabwt_single(Y: np.ndarray, gg: dict[str, np.ndarray], casewt: np.ndarray, last: np.ndarray | None) -> np.ndarray:
    ny = Y.shape[1]
    index = _find_interval(Y[:, ny - 2 if ny > 2 else 0], gg["time"], left_open=True)
    gwt = np.concatenate(([1.0], gg["surv"]))[1 + index]
    if ny == 2:
        haswt = Y[:, 1] > 0
    else:
        haswt = last & (Y[:, 2] > 0)
    out = np.zeros_like(casewt, dtype=float)
    np.divide(casewt, gwt, out=out, where=haswt)
    return out


def _grabwt_matrix(
    Y: np.ndarray,
    gg: dict[str, np.ndarray],
    casewt: np.ndarray,
    last: np.ndarray | None,
    times: np.ndarray,
) -> np.ndarray:
    ny = Y.shape[1]
    indx = _find_interval(times, gg["time"], left_open=True)
    gwt = np.concatenate(([1.0], gg["surv"]))[1 + indx]
    indx2 = _find_interval(Y[:, ny - 2 if ny > 2 else 0], gg["time"], left_open=True)
    gwt2 = np.concatenate(([1.0], gg["surv"]))[1 + indx2]
    ntime = len(times)
    n = Y.shape[0]
    if ny == 2:
        wtmat = np.where(
            np.greater.outer(Y[:, 0], times),
            np.divide.outer(casewt, gwt),
            0.0,
        )
        indx3 = Y[:, 1] > 0
        wtmat[indx3, :] = casewt[indx3, np.newaxis] / np.maximum.outer(gwt2[indx3], gwt)
    else:
        inner = np.less.outer(Y[:, 0], times) & np.greater_equal.outer(Y[:, 1], times)
        wtmat = np.where(inner, np.divide.outer(casewt, gwt), 0.0)
        indx3 = (Y[:, 1] > 0) & last
        wtmat[indx3, :] = casewt[indx3, np.newaxis] / np.maximum.outer(gwt2[indx3], gwt)
    return wtmat


def rttright(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action=None,
    times=None,
    id=None,
    timefix=True,
    renorm=True,
):
    """Compute redistribute-to-the-right weights."""
    if formula is None:
        raise ValueError("a formula argument is required")
    if not isinstance(formula, str):
        raise ValueError("a formula argument is required")
    if data is None:
        raise ValueError("data argument is required")

    mf = _build_model_frame(
        formula,
        data,
        subset=subset,
        weights=weights,
        na_action=na_action,
        id=id,
        istate=None,
    )
    n = len(mf)
    Y_obj = _model_response(mf)
    if not is_Surv(Y_obj):
        raise ValueError("response must be a Surv object")
    kind = Y_obj.type
    if kind not in ("right", "mright", "counting", "mcounting"):
        raise ValueError("response must be right censored")

    terms = _build_terms(formula, mf.names, _term_labels_from_formula(formula, mf.names))
    order = terms["order"]
    if order and any(int(o) != 1 for o in order):
        raise ValueError("Interaction terms are not valid for this function")

    Y = np.array(Y_obj.columns, dtype=float, copy=True)
    ny = Y.shape[1]

    casewt = _model_extract(mf, "weights")
    if casewt is None:
        casewt = np.ones(n, dtype=float)
    else:
        casewt = np.asarray(casewt, dtype=float)
        if not np.issubdtype(casewt.dtype, np.number):
            raise ValueError("weights must be numeric")
        if not np.all(np.isfinite(casewt)):
            raise ValueError("weights must be finite")
        if np.any(casewt < 0):
            raise ValueError("weights must be non-negative")
        casewt = casewt.astype(float, copy=False)

    if terms.get("offset") is not None:
        warnings.warn("Offset term ignored", RuntimeWarning, stacklevel=2)

    cluster_temp = untangle_specials(terms, "cluster", 1)
    term_labels = list(terms["term.labels"])
    if cluster_temp.get("terms"):
        drop = [int(t) - 1 for t in cluster_temp["terms"]]
        term_labels = [lab for i, lab in enumerate(term_labels) if i not in drop]

    if not term_labels:
        istrat = np.ones(n, dtype=int)
    else:
        cols = []
        for lab in term_labels:
            if _parse_cluster_term(lab):
                continue
            idx = mf.names.index(lab)
            col = mf.columns[idx]
            if isinstance(col, list):
                col = np.asarray(col, dtype=object)
            cols.append(col)
        if len(cols) == 1:
            X = strata_fn(cols[0])
        else:
            X = strata_fn(*cols, shortlabel=True)
        istrat = _as_numeric_strata(X)

    if not (isinstance(timefix, (bool, np.bool_)) and np.asarray(timefix).size == 1):
        raise ValueError("invalid value for timefix option")
    if timefix:
        Y_obj = aeqSurv(Y_obj)
        Y = np.array(Y_obj.columns, dtype=float, copy=True)

    id_col = _model_extract(mf, "id")
    if ny == 3 and id_col is None:
        raise ValueError("id is required for start-stop data")

    check = None
    if id_col is not None:
        y_check = Y_obj
        if y_check.states is None:
            y_check = SurvObject(Y_obj.columns, Y_obj.type, ["event"], Y_obj.clabel)
        check = _survcheck2(y_check, id_col)
        if any(int(v) > 0 for v in check["flag"].values()):
            raise ValueError("one or more flags are >0 in survcheck")
        n_startstate = int(np.sum(check["transitions"][:, 0] > 1))
        if ny == 2:
            samestart = True
        else:
            id_arr = np.asarray(id_col, dtype=object)
            etemp = np.array([np.min(Y[id_arr == subj, 0]) for subj in np.unique(id_arr)])
            samestart = bool(np.all(etemp == etemp[0]))
        id_arr = np.asarray(id_col, dtype=object)
        for subj in np.unique(id_arr):
            wsub = casewt[id_arr == subj]
            if wsub.size and np.ptp(wsub) > 0:
                raise ValueError("there are subjects with multiple weights")
    else:
        n_startstate = 0
        samestart = True

    single_time = times is None
    if single_time:
        times_arr = np.array([0.0])
    else:
        times_arr = np.asarray(times, dtype=float).reshape(-1)

    if check is None or (n_startstate == 1 and samestart):
        nstrat = int(np.max(istrat))
        if renorm:
            casewt = casewt.copy()
            for i in np.unique(istrat):
                j = np.where(istrat == i)[0]
                if id_col is None:
                    uj = j
                else:
                    id_arr = np.asarray(id_col, dtype=object)
                    dup = _duplicated(id_arr[j], from_last=False)
                    uj = j[~dup]
                casewt[j] = casewt[j] / np.sum(casewt[uj])

        last = None
        if ny == 2:
            censor = np.where(Y[:, 1] == 0, 1.0, 0.0)
        else:
            id_arr = np.asarray(id_col, dtype=object)
            ord_idx = np.lexsort((Y[:, 1], id_arr))
            ltemp = ~_duplicated(id_arr[ord_idx], from_last=True)
            last = ltemp[np.argsort(ord_idx)]
            censor = np.where(last & (Y[:, 2] == 0), 1.0, 0.0)

        uniq = np.unique(np.concatenate([Y[:, : ny - 1].reshape(-1), times_arr]))
        uniq = np.sort(uniq[~np.isnan(uniq)])
        delta = float(np.min(np.diff(uniq))) / 2 if uniq.size > 1 else 0.5
        y2 = Y.copy()
        y2[:, -1] = censor
        if np.any(censor == 1):
            y2[censor == 1, ny - 2] = y2[censor == 1, ny - 2] + delta
        y2_use = y2

        G = _survfit_km(y2_use, istrat, casewt)

        if single_time:
            wtmat = np.zeros((n, 1), dtype=float)
            for i in range(1, nstrat + 1):
                who = istrat == i
                wtmat[who, 0] = _grabwt_single(Y[who], G[i], casewt[who], last[who] if last is not None else None)
        else:
            wtmat = np.zeros((n, len(times_arr)), dtype=float)
            for i in range(1, nstrat + 1):
                who = istrat == i
                wtmat[who, :] = _grabwt_matrix(
                    Y[who],
                    G[i],
                    casewt[who],
                    last[who] if last is not None else None,
                    times_arr,
                )
    else:
        raise ValueError("function not defined for delayed entry or multistate data")

    if not single_time:
        return wtmat
    return wtmat.reshape(-1)


def _term_labels_from_formula(formula: str, mf_names: list[str]) -> list[str]:
    rhs = formula.split("~", 1)[1].strip()
    labels: list[str] = []
    for term in _split_rhs_terms(rhs):
        if term == "1":
            continue
        if term == ".":
            labels.extend(name for name in mf_names[1:] if not name.startswith("("))
        elif _parse_cluster_term(term):
            labels.append(term)
        else:
            labels.append(term)
    return labels
