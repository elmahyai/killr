"""Log-linear models (MASS loglm and internal loglm1 / loglin front-end)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Mapping, Sequence

import numpy as np

from mass.errors import MassError


@dataclass
class Terms:
    """Minimal ``terms`` object for ``loglm1``."""

    formula: str
    term_labels: list[str]
    factors: np.ndarray
    row_names: list[str]
    response: int
    intercept: int = 1


@dataclass
class LoglmResult:
    """Fitted log-linear model (R class ``loglm``)."""

    lrt: float
    pearson: float
    df: float
    margin: list[Any]
    nobs: int
    deviance: float
    terms: Terms | None = None
    call: Any = None
    formula: str | None = None
    fit: np.ndarray | None = None
    param: Any = None
    frequencies: np.ndarray | None = None
    fitted: np.ndarray | None = None


def _denumerate_name(name: str) -> str:
    if name and name[0] in "123456789":
        return f".v{name}"
    return name


def _renumerate_name(name: str) -> str:
    if name.startswith(".v") and len(name) > 2:
        return name[2:]
    return name


def _split_formula(formula: str) -> tuple[str | None, str]:
    if not isinstance(formula, str):
        raise MassError("formula must be a character string")
    text = formula.strip()
    if "~" not in text:
        raise MassError("invalid formula")
    lhs, rhs = text.split("~", 1)
    lhs = lhs.strip()
    return (lhs if lhs else None, rhs.strip())


def _expand_term_piece(piece: str) -> list[str]:
    piece = piece.strip()
    if not piece:
        return []
    if piece == "1":
        return []
    if piece == ".":
        raise MassError("'.' in formula requires a data frame with named columns")
    if "*" in piece:
        vars_ = [v.strip() for v in piece.split("*") if v.strip()]
        out: list[str] = []
        for r in range(1, len(vars_) + 1):
            for combo in combinations(vars_, r):
                out.append(":".join(combo))
        return out
    return [piece.replace(" ", "")]


def _expand_rhs(rhs: str) -> list[str]:
    terms: list[str] = []
    has_intercept = False
    for part in rhs.split("+"):
        part = part.strip()
        if part in ("1", "0"):
            if part == "1":
                has_intercept = True
            continue
        for term in _expand_term_piece(part):
            if term not in terms:
                terms.append(term)
    if not has_intercept and not terms:
        has_intercept = True
    return terms


def _term_variables(term: str) -> list[str]:
    if ":" in term:
        return term.split(":")
    return [term]


def _build_terms(formula: str, variable_names: Sequence[str], *, denumerate: bool = False) -> Terms:
    response_name, rhs = _split_formula(formula)
    response = 0
    row_names = list(variable_names)
    if denumerate:
        row_names = [_denumerate_name(v) for v in row_names]
    term_labels = _expand_rhs(rhs)
    if response_name is not None:
        resp = _denumerate_name(response_name.strip()) if denumerate else response_name.strip()
        try:
            response = row_names.index(resp) + 1
        except ValueError as exc:
            raise MassError(f"response '{response_name}' not found in data") from exc
    n = len(row_names)
    mat = np.zeros((n, len(term_labels)), dtype=bool)
    for j, label in enumerate(term_labels):
        vars_in_term = _term_variables(label)
        for v in vars_in_term:
            vkey = _denumerate_name(v) if denumerate else v
            if vkey not in row_names:
                raise MassError(f"variable '{v}' not found")
            mat[row_names.index(vkey), j] = True
    return Terms(
        formula=formula,
        term_labels=term_labels,
        factors=mat,
        row_names=row_names,
        response=response,
    )


def _subsets(x: Sequence[int]) -> list[list[int]]:
    y: list[list[int]] = [[]]
    for item in x:
        y = y + [s + [item] for s in y]
    return y[1:]


def _loglin_df(dtab: Sequence[int], margin_idx: list[list[int]]) -> float:
    nvar = len(dtab)
    df = [0.0] * (2**nvar)
    for margin in margin_idx:
        for term in _subsets(margin):
            bit = sum(2 ** (t - 1) for t in term)
            prod = 1.0
            for t in term:
                prod *= dtab[t - 1] - 1
            df[bit] = prod
    ntab = int(np.prod(dtab))
    return float(ntab - sum(df) - 1)


def _resolve_margin_indices(margin: list[Any], varnames: list[str]) -> list[list[int]]:
    out: list[list[int]] = []
    for m in margin:
        items = m if isinstance(m, (list, tuple)) else [m]
        idx: list[int] = []
        for t in items:
            if isinstance(t, str):
                if t not in varnames:
                    raise MassError("'margin' must contain names corresponding to 'table'")
                idx.append(varnames.index(t) + 1)
            else:
                ti = int(t)
                if ti <= 0 or ti > len(varnames):
                    raise MassError("'margin' must contain names or numbers corresponding to 'table'")
                idx.append(ti)
        out.append(idx)
    return out


def _iterative_proportional_scaling(
    table: np.ndarray,
    margin_idx: list[list[int]],
    start: np.ndarray,
    *,
    eps: float = 0.1,
    max_iter: int = 40,
    print_iter: bool = False,
) -> tuple[np.ndarray, int, float]:
    table = np.asarray(table, dtype=float)
    fit = np.asarray(start, dtype=float).reshape(table.shape).copy()
    nvar = table.ndim
    nlast = 0
    dev_last = 0.0
    for nlast in range(1, max_iter + 1):
        old = fit.copy()
        for idx in margin_idx:
            margin_axes = {i - 1 for i in idx}
            sum_axes = tuple(sorted(set(range(nvar)) - margin_axes))
            if sum_axes:
                obs_m = table.sum(axis=sum_axes, keepdims=True)
                fit_m = fit.sum(axis=sum_axes, keepdims=True)
            else:
                obs_m = table
                fit_m = fit
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(fit_m > 0, obs_m / fit_m, 0.0)
            fit = fit * ratio
        dev_last = float(np.max(np.abs(fit - old) / np.maximum(old, 1e-10)))
        if dev_last < eps:
            break
    if print_iter:
        if nlast > 0:
            print(f"{nlast} iterations: deviation {dev_last}")
        else:
            print(f"{nlast} iterations")
    return fit, nlast, dev_last


def _loglin_parameters(
    fit: np.ndarray,
    dtab: Sequence[int],
    margin_idx: list[list[int]],
    varnames: list[str],
) -> dict[str, float]:
    df_bits = [0.0] * (2 ** len(dtab))
    for margin in margin_idx:
        for term in _subsets(margin):
            bit = sum(2 ** (t - 1) for t in term)
            prod = 1.0
            for t in term:
                prod *= dtab[t - 1] - 1
            df_bits[bit] = prod
    terms_idx = [i for i, v in enumerate(df_bits) if v > 0]
    parlen = len(terms_idx) + 1
    log_fit = np.log(np.where(fit > 0, fit, np.nan))
    parval: list[float] = [float(np.nanmean(log_fit))]
    parnam = ["(Intercept)"]
    log_fit = log_fit - parval[0]
    if parlen > 1:
        dyadic = []
        terms_copy = list(terms_idx)
        while any(t > 0 for t in terms_copy):
            dyadic.append([t % 2 for t in terms_copy])
            terms_copy = [t // 2 for t in terms_copy]
        dyadic_arr = np.array(dyadic).T
        order = np.argsort(dyadic_arr.sum(axis=1))
        dyadic_arr = dyadic_arr[order]
        for i in range(1, parlen):
            vars_ = np.where(dyadic_arr[i - 1] > 0)[0]
            slice_obj: list[Any] = [slice(None)] * fit.ndim
            for v in vars_:
                slice_obj[v] = 0
            parval.append(float(np.nanmean(log_fit[tuple(slice_obj)])))
            parnam.append(":".join(varnames[v] for v in vars_))
            log_fit = log_fit - parval[-1]
    return dict(zip(parnam, parval))


def _loglin(
    table: np.ndarray,
    margin: list[Any],
    start: Sequence[float] | np.ndarray,
    *,
    varnames: Sequence[str] | None = None,
    fit: bool = False,
    param: bool = False,
    eps: float = 0.1,
    max_iter: int = 40,
    print: bool = False,
) -> dict[str, Any]:
    table = np.asarray(table, dtype=float)
    dtab = list(table.shape)
    if varnames is None:
        anames = getattr(table, "_dimnames", None)
        varnames = list(anames) if anames else [str(i + 1) for i in range(len(dtab))]
    else:
        varnames = list(varnames)
    margin_idx = _resolve_margin_indices(margin, varnames)
    start_arr = np.asarray(start, dtype=float)
    if start_arr.size != table.size:
        raise MassError("'start' and 'table' must be same length")
    fit_arr, _, _ = _iterative_proportional_scaling(
        table, margin_idx, start_arr, eps=eps, max_iter=max_iter, print_iter=print
    )
    observed = table.ravel()[start_arr.ravel() > 0]
    expected = fit_arr.ravel()[start_arr.ravel() > 0]
    pearson = float(np.sum((observed - expected) ** 2 / expected))
    mask = (table.ravel() * fit_arr.ravel()) > 0
    observed2 = table.ravel()[mask]
    expected2 = fit_arr.ravel()[mask]
    lrt = float(2 * np.sum(observed2 * np.log(observed2 / expected2)))
    df = _loglin_df(dtab, margin_idx)
    margin_out: list[Any] = []
    for idx in margin_idx:
        margin_out.append([varnames[i - 1] for i in idx])
    if len(margin_out) == 1:
        pass
    result: dict[str, Any] = {"lrt": lrt, "pearson": pearson, "df": df, "margin": margin_out}
    if fit:
        result["fit"] = fit_arr
    if param:
        result["param"] = _loglin_parameters(fit_arr, dtab, margin_idx, varnames)
    return result


def _margins_from_terms(trms: Terms, data: np.ndarray) -> list[list[int]]:
    factors = trms.factors.astype(bool)
    r = trms.response
    if r:
        keep_rows = [i for i in range(factors.shape[0]) if i != r - 1]
        factors = factors[keep_rows, :]
        rownames = [trms.row_names[i] for i in keep_rows]
    else:
        rownames = list(trms.row_names)
    nt = factors.shape[1]
    if nt == 0:
        return []
    col_sums = factors.sum(axis=0)
    order = np.argsort(col_sums)
    factors = factors[:, order]
    labels = [trms.term_labels[i] for i in order]
    ff = factors.T @ factors
    keep = np.ones(nt, dtype=bool)
    for j in range(nt - 1):
        if j + 1 < nt:
            keep[j] = ff[j, j] > ff[j, j + 1 :].max()
    factors = factors[:, keep]
    labels = [labels[i] for i in range(nt) if keep[i]]
    ldim = data.ndim
    nnames = [f".v{i}" for i in range(1, ldim + 1)]
    which: dict[str, int] = {name: i + 1 for i, name in enumerate(nnames)}
    anames = getattr(data, "_dimnames", None) or []
    if anames:
        for i, name in enumerate(anames):
            which[name] = i + 1
    margins: list[list[int]] = []
    for j in range(factors.shape[1]):
        vars_in = [rownames[i] for i in range(len(rownames)) if factors[i, j]]
        idx = [which[v] for v in vars_in]
        margins.append(idx)
    return margins


class _FreqArray(np.ndarray):
    """N-dimensional frequency table carrying dimnames and optional terms."""

    _dimnames: list[str] | None
    terms: Terms | None

    def __new__(cls, input_array: np.ndarray, dimnames: list[str] | None = None, terms: Terms | None = None):
        obj = np.asarray(input_array).view(cls)
        obj._dimnames = dimnames
        obj.terms = terms
        return obj


def _as_factor(values: Sequence[Any]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for v in values:
        key = str(v)
        if key not in seen:
            seen[key] = len(seen)
        out.append(key)
    return out


def _model_frame(formula: str, data: Mapping[str, Sequence[Any]]) -> tuple[dict[str, list[Any]], Terms]:
    response, rhs = _split_formula(formula)
    columns = list(data.keys())
    if response is None:
        raise MassError("model.frame requires a response for data frame loglm")
    if response not in data:
        raise MassError(f"variable '{response}' not found")
    terms = _build_terms(formula, columns, denumerate=False)
    n = len(data[response])
    frame = {response: list(data[response])}
    for label in terms.term_labels:
        for var in _term_variables(label):
            if var not in frame and var in data:
                frame[var] = list(data[var])
    for key in frame:
        if len(frame[key]) != n:
            raise MassError("variable lengths differ")
    return frame, terms


def _loglm1_default(
    formula: str,
    data: _FreqArray,
    *,
    start: np.ndarray | None = None,
    fitted: bool = False,
    keep_frequencies: bool = False,
    param: bool = True,
    eps: float = 0.1,
    max_iter: int = 40,
    print: bool = False,
    _call: Any = None,
    _formula: str | None = None,
) -> LoglmResult:
    trms = data.terms
    if trms is None:
        raise MassError("'data' has no 'terms' attribute")
    if start is None:
        start = np.ones(data.size, dtype=float)
    margin_idx = _margins_from_terms(trms, data)
    anames = data._dimnames or [str(i + 1) for i in range(data.ndim)]
    anames = data._dimnames or [str(i + 1) for i in range(data.ndim)]
    margin_named = [[anames[i - 1] for i in m] for m in margin_idx]
    fit_out = _loglin(
        np.asarray(data),
        margin_named,
        start,
        varnames=anames,
        fit=fitted,
        param=param,
        eps=eps,
        max_iter=max_iter,
        print=print,
    )
    df = fit_out["df"] - int(np.sum(np.asarray(start).ravel() == 0))
    result = LoglmResult(
        lrt=fit_out["lrt"],
        pearson=fit_out["pearson"],
        df=df,
        margin=fit_out["margin"],
        nobs=int(data.size),
        deviance=fit_out["lrt"],
        terms=trms,
        call=_call,
        formula=_formula or formula,
    )
    if keep_frequencies:
        result.frequencies = np.asarray(data).copy()
    if fitted and "fit" in fit_out:
        result.fitted = fit_out["fit"]
        result.fit = fit_out["fit"]
    if param and "param" in fit_out:
        result.param = fit_out["param"]
    return result


def _loglm1_data_frame(
    formula: str,
    data: Mapping[str, Sequence[Any]],
    terms: Terms,
    **kwargs: Any,
) -> LoglmResult:
    trms = terms
    if trms.response == 0:
        raise MassError("formula specifies no response")
    resp = trms.row_names[trms.response - 1]
    off_cols: set[str] = set()
    frame_keys = list(data.keys())
    resp_idx = frame_keys.index(resp) if resp in frame_keys else -1
    pred_cols = [c for c in frame_keys if c != resp]
    fac_data = {c: _as_factor(data[c]) for c in pred_cols}
    rsp = list(data[resp])
    n = len(rsp)
    levels = {c: sorted(set(fac_data[c])) for c in pred_cols}
    # build table counts via dict
    from collections import Counter

    counts: Counter[tuple[str, ...]] = Counter()
    rows_keys: list[tuple[str, ...]] = []
    for i in range(n):
        key = tuple(fac_data[c][i] for c in pred_cols)
        counts[key] += 1
        rows_keys.append(key)
    tab_counts = list(counts.values())
    if max(tab_counts) > 1:
        order = sorted(range(n), key=lambda i: tuple(fac_data[c][i] for c in reversed(pred_cols)))
        fac_data = {c: [fac_data[c][i] for i in order] for c in pred_cols}
        rsp = [rsp[i] for i in order]
        within: list[int] = []
        from itertools import groupby

        def row_key(i: int) -> tuple[str, ...]:
            return tuple(fac_data[c][i] for c in pred_cols)

        for _, group in groupby(range(n), key=row_key):
            grp = list(group)
            cell_count = len(grp)
            for seq in range(1, cell_count + 1):
                within.append(seq)
        pred_cols = pred_cols + [".Within."]
        fac_data[".Within."] = [str(w) for w in within]
        levels[".Within."] = [str(i) for i in range(1, max(within) + 1)]
    dm = [len(levels[c]) for c in pred_cols]
    dn = [levels[c] for c in pred_cols]
    arr = np.full(dm, -1.0)
    index_map = {c: {lev: i for i, lev in enumerate(levels[c])} for c in pred_cols}
    for i in range(n):
        idx = tuple(index_map[c][fac_data[c][i]] for c in pred_cols)
        arr[idx] = float(rsp[i])
    st = np.where(arr >= 0, 1.0, 0.0)
    arr[arr < 0] = 0.0
    freq = _FreqArray(arr, dimnames=pred_cols, terms=trms)
    start = st.astype(float)
    return _loglm1_default(formula, freq, start=start, **kwargs)


def loglm(
    formula: str,
    data: np.ndarray | Mapping[str, Sequence[Any]] | None = None,
    subset: Sequence[int] | None = None,
    na_action: Any = None,
    **kwargs: Any,
) -> LoglmResult:
    """Fit a log-linear model (MASS ``loglm``)."""
    call = ("loglm", formula, data)
    if data is None or (isinstance(data, dict) and not isinstance(data, np.ndarray)):
        if data is None:
            raise MassError("'data' is required")
        frame, terms = _model_frame(formula, data)
        if subset is not None:
            frame = {k: [v[i] for i in subset] for k, v in frame.items()}
        out_formula = formula
        return _loglm1_data_frame(
            formula,
            frame,
            terms,
            _call=call,
            _formula=out_formula,
            **kwargs,
        )
    if isinstance(data, np.ndarray):
        array = np.asarray(data, dtype=float)
        trms = _build_terms(formula, list(getattr(data, "_dimnames", []) or []), denumerate=True)
        renumerate_formula = formula
        freq = _FreqArray(array, dimnames=getattr(data, "_dimnames", None), terms=trms)
        return _loglm1_default(
            formula,
            freq,
            _call=call,
            _formula=renumerate_formula,
            **kwargs,
        )
    raise MassError("unsupported 'data' type")
