"""Population marginal means (survival::yates)."""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass
from itertools import product
from typing import Any, Mapping

import numpy as np

from survival._yates_mm import Terms, YatesError, _match_arg, _split_formula, build_terms, lm_fit, model_matrix


def _as_dict(fit: Any) -> dict[str, Any]:
    if isinstance(fit, dict):
        return fit
    out: dict[str, Any] = {}
    for key in (
        "class",
        "coefficients",
        "coef",
        "coef_names",
        "vcov",
        "model",
        "terms",
        "xlevels",
        "contrasts",
        "assign",
        "sigma",
        "formula",
        "x",
        "means",
    ):
        if hasattr(fit, key):
            out[key] = getattr(fit, key)
    return out


def _fit_class(fit: dict[str, Any]) -> str:
    klass = fit.get("class", ["default"])
    if isinstance(klass, str):
        return klass
    return klass[0] if klass else "default"


def _terms_attributes(terms: Terms) -> dict[str, Any]:
    row_names = terms.variables
    data_classes = {name: terms.data_classes[name] for name in row_names}
    return {
        "term.labels": terms.term_labels,
        "variables": terms.variables,
        "dataClasses": data_classes,
        "factors": terms.factors,
        "intercept": 1 if terms.intercept else 0,
    }


def _delete_response_terms(terms: Terms) -> Terms:
    variables = list(terms.variables)
    if not variables:
        return terms
    response = variables[0]
    new_vars = variables[1:]
    data_classes = {k: v for k, v in terms.data_classes.items() if k != response}
    factors = terms.factors[1:, :]
    return Terms(
        formula=terms.formula,
        response=response,
        intercept=terms.intercept,
        term_labels=terms.term_labels,
        variables=[response] + new_vars,
        data_classes=terms.data_classes,
        factors=factors,
        predvars=terms.predvars,
    )


def _gsolve(mat: np.ndarray, y: np.ndarray, eps: float | None = None) -> tuple[np.ndarray, int]:
    if eps is None:
        eps = math.sqrt(np.finfo(float).eps)
    mat = np.asarray(mat, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    u, s, _vh = np.linalg.svd(mat, full_matrices=False)
    if s.size == 0:
        return np.zeros_like(y), 0
    dpos = s > max(s[0] * eps, 0.0)
    dd = np.where(dpos, 1.0 / s, 0.0)
    if np.all(dpos):
        x = u @ (dd * (u.T @ y))
    elif not np.any(dpos):
        x = np.zeros_like(y)
    else:
        uu = u[:, dpos]
        x = uu @ (dd[dpos] * (uu.T @ y))
    return np.asarray(x, dtype=float).reshape(-1), int(np.sum(dpos))


def _qform(var: np.ndarray, beta: np.ndarray) -> tuple[float, int]:
    temp, df = _gsolve(var, beta)
    return float(np.sum(beta * temp)), df


def _estfun(cmat: np.ndarray, beta: np.ndarray, varmat: np.ndarray) -> dict[str, Any]:
    cmat = np.asarray(cmat, dtype=float)
    beta = np.asarray(beta, dtype=float).reshape(-1)
    varmat = np.asarray(varmat, dtype=float)
    nabeta = np.isnan(beta)
    if np.any(nabeta):
        keep = np.where(~nabeta)[0]
        estimate = cmat[:, keep] @ beta[keep]
        evar = cmat[:, keep] @ varmat @ cmat[:, keep].T
    else:
        estimate = cmat @ beta
        evar = cmat @ varmat @ cmat.T
    return {"estimate": np.asarray(estimate, dtype=float).reshape(-1), "var": np.asarray(evar, dtype=float)}


def _testfun(
    cmat: np.ndarray,
    beta: np.ndarray,
    varmat: np.ndarray,
    sigma2: float | None,
) -> dict[str, float]:
    cmat = np.asarray(cmat, dtype=float)
    beta = np.asarray(beta, dtype=float).reshape(-1)
    varmat = np.asarray(varmat, dtype=float)
    nabeta = np.isnan(beta)
    if np.any(nabeta):
        keep = np.where(~nabeta)[0]
        estimate = cmat[:, keep] @ beta[keep]
        temp, df = _qform(cmat[:, keep] @ varmat @ cmat[:, keep].T, estimate)
    else:
        estimate = cmat @ beta
        temp, df = _qform(cmat @ varmat @ cmat.T, estimate)
    out = {"chisq": temp, "df": float(df)}
    if sigma2 is not None:
        out["ss"] = temp * sigma2
    return out


def _nafun(cmat: np.ndarray, est: np.ndarray) -> bool:
    cmat = np.atleast_2d(np.asarray(cmat, dtype=float))
    est = np.asarray(est, dtype=float).reshape(-1)
    used = np.any(cmat != 0, axis=0)
    return bool(np.any(used & np.isnan(est)))


def _expand_grid(level_lists: list[list[Any]]) -> list[dict[str, Any]]:
    keys = [f"x{i}" for i in range(len(level_lists))]
    rows = []
    for combo in product(*level_lists):
        rows.append(dict(zip(keys, combo)))
    return rows


def _cmatrix(
    fit: dict[str, Any],
    term: Any,
    *,
    test: str = "global",
    levels: Any = None,
    assign: list[int] | None = None,
) -> dict[str, Any]:
    terms = fit["terms"]
    if not isinstance(terms, Terms):
        raise YatesError("the fit does not have a terms structure")
    tatt = _terms_attributes(terms)
    test = _match_arg(test, ["global", "trend", "pairwise", "mean"])

    if term is None:
        raise YatesError("a term argument is required")
    if isinstance(term, str):
        text = term.strip()
        if not text.startswith("~"):
            text = f"~ {text}"
        _, rhs = _split_formula(f"y {text}")
        term_labels, _vars = _parse_term_rhs(rhs)
        termname = _vars
    elif isinstance(term, (list, tuple)) and term and isinstance(term[0], (int, np.integer)):
        idx = [int(t) for t in term]
        labels = tatt["term.labels"]
        if not all(i == math.floor(i) and 0 < i < len(labels) for i in idx):
            raise YatesError("a numeric term must be an integer between 1 and max terms in the fit")
        termname = [labels[i - 1] for i in idx]
    else:
        raise YatesError("the term must be a formula or integer")

    key = []
    for var in terms.variables[1:]:
        key.append(var.split("(")[0].strip() if "(" in var else var)
    parts = []
    for name in termname:
        try:
            parts.append(terms.variables[1:][key.index(name)])
        except ValueError:
            parts.append(name)
    types = [tatt["dataClasses"][p] for p in parts]
    iscat = [1 if t in {"factor", "character"} else 0 for t in types]
    if len(iscat) == 1:
        termtype = iscat[0]
    else:
        termtype = 2 + int(any(iscat)) + int(all(iscat))

    xlevels = fit.get("xlevels") or {}
    if levels is None:
        temp = [xlevels.get(p) for p in parts]
        if any(t is None for t in temp):
            raise YatesError("continuous variables require the levels argument")
        grid = _expand_grid(temp)
        level_rows = [{parts[i]: grid[j][f"x{i}"] for i in range(len(parts))} for j in range(len(grid))]
    else:
        level_rows = _normalize_levels(levels, termname, parts, xlevels)

    for i, is_cat in enumerate(iscat):
        if not is_cat:
            continue
        xlev = xlevels.get(parts[i])
        if xlev is None:
            raise YatesError(f"xlevels attribute not found for{termname[i]}")
        for row in level_rows:
            val = str(row[parts[i]])
            if val not in xlev:
                raise YatesError(f"invalid level for term{termname[i]}")

    if test == "global":
        nlev = len(level_rows)
        cmat = np.eye(nlev, dtype=float)
        cmat[:, -1] = -1.0
        cmat = cmat[:-1, :]
    elif test == "pairwise":
        nlev = len(level_rows)
        if nlev < 2:
            raise YatesError("pairwise tests need at least 2 groups")
        pairs = []
        names = []
        for i in range(nlev - 1):
            for j in range(i + 1, nlev):
                row = np.zeros(nlev)
                row[i] = 1.0
                row[j] = -1.0
                pairs.append(row)
                names.append(f"{i + 1} vs {j + 1}")
        cmat = np.vstack(pairs) if len(pairs) > 1 else pairs[0].reshape(1, -1)
        if len(pairs) > 1:
            cmat = {names[k]: pairs[k].reshape(1, -1) for k in range(len(pairs))}
    elif test == "mean":
        nlev = len(level_rows)
        cmat = {}
        for k in range(nlev):
            row = np.full(nlev, -1.0 / nlev)
            row[k] = (nlev - 1) / nlev
            cmat[f"{k + 1} vs mean"] = row.reshape(1, -1)
    else:
        ntest = len(level_rows)
        cmat = {"trend": np.arange(1, ntest + 1, dtype=float).reshape(1, -1), "identity": np.eye(ntest)}
        if level_rows and level_rows[0].get(parts[0]) is None:
            raise YatesError("don't know how to do a linear contrast for this term")

    return {
        "levels": level_rows,
        "termname": parts,
        "cmat": cmat,
        "iscat": iscat,
        "class": "cmatrix",
    }


def _parse_term_rhs(rhs: str) -> tuple[list[str], list[str]]:
    pieces = [p.strip() for p in rhs.split("+") if p.strip()]
    vars_seen: list[str] = []
    labels: list[str] = []
    for piece in pieces:
        if ":" in piece:
            labels.append(piece)
            for part in piece.split(":"):
                if part not in vars_seen:
                    vars_seen.append(part)
        elif "*" in piece:
            parts = [p.strip() for p in piece.split("*") if p.strip()]
            for part in parts:
                if part not in vars_seen:
                    vars_seen.append(part)
            labels.append(":".join(parts))
        else:
            labels.append(piece)
            if piece not in vars_seen:
                vars_seen.append(piece)
    return labels, vars_seen


def _normalize_levels(levels: Any, termname: list[str], parts: list[str], xlevels: dict) -> list[dict[str, Any]]:
    if isinstance(levels, Mapping):
        level_map = dict(levels)
    elif isinstance(levels, list):
        if len(parts) == 1:
            level_map = {parts[0]: levels}
        else:
            raise YatesError("levels list requires named elements")
    else:
        if len(parts) > 1:
            raise YatesError("levels should be a data frame or matrix")
        level_map = {parts[0]: list(dict.fromkeys(levels))}

    merged = {}
    for name in termname:
        if name in level_map:
            merged[name] = list(level_map[name])
        elif parts[termname.index(name)] in xlevels:
            merged[name] = list(xlevels[parts[termname.index(name)]])
        else:
            raise YatesError(f"levels information not found for: {name}")
    keys = [merged[name] for name in termname]
    rows = []
    for combo in product(*keys):
        rows.append({termname[i]: combo[i] for i in range(len(termname))})
    seen = set()
    out = []
    for row in rows:
        key = tuple(row.values())
        if key in seen:
            raise YatesError("levels data frame has duplicates")
        seen.add(key)
        out.append({parts[termname.index(k)]: v for k, v in row.items()})
    return out


def _yates_factorial_pop(mframe: dict[str, Any], terms: Terms, x2indx: dict[str, bool], xlevels: dict) -> dict[str, Any]:
    x2name = [name for name, flag in x2indx.items() if flag]
    dclass = {name: terms.data_classes.get(name, "numeric") for name in x2name}
    if not all(dclass[n] in {"character", "factor"} for n in x2name):
        raise YatesError("population=factorial only applies if all the adjusting terms are categorical")
    n2 = [len(xlevels[name]) for name in x2name]
    n = int(np.prod(n2))
    keys = [k for k in mframe if k != terms.response]
    pdata: dict[str, Any] = {}
    template = {k: mframe[k][0] for k in keys}
    for _ in range(n):
        for k, v in template.items():
            pdata.setdefault(k, []).append(v)
    n1 = 1
    for i, name in enumerate(x2name):
        xx = xlevels[name]
        pattern = []
        for lev_idx in range(n2[i]):
            pattern.extend([lev_idx + 1] * n1)
        pattern = (pattern * (n // len(pattern)))[:n]
        if dclass[name] == "factor":
            pdata[name] = [xx[idx - 1] for idx in pattern]
        else:
            pdata[name] = [xx[idx - 1] for idx in pattern]
        n1 *= n2[i]
    pdata["_terms"] = terms
    return pdata


def _frame_to_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _yates_xmat(
    terms: Terms,
    tatt: dict[str, Any],
    contr: dict[str, Any],
    population: Any,
    mframe: dict[str, Any],
    fit: dict[str, Any],
    iscat: dict[str, bool],
) -> list[np.ndarray]:
    colnames = terms.variables[1:]
    factor_mat = terms.factors
    termname = contr["termname"]
    label_indices: list[int] = []
    for tn in termname:
        if tn in terms.term_labels:
            label_indices.append(terms.term_labels.index(tn))
        else:
            label_indices.extend(j for j, lbl in enumerate(terms.term_labels) if tn in lbl.split(":"))
    if not label_indices:
        if len(termname) > 1:
            raise YatesError("incomplete code 1")
        x1indx = {name: name == termname[0] for name in colnames}
    else:
        x1indx = {}
        for i, name in enumerate(colnames):
            x1indx[name] = any(factor_mat[i, j] > 0 for j in label_indices)

    x2indx = {name: not flag for name, flag in x1indx.items()}
    xlevels = fit.get("xlevels") or {}
    contrasts = fit.get("contrasts") or {}

    if isinstance(population, dict) and "_terms" not in population:
        pdata = population
        pop_terms = None
    elif isinstance(population, str):
        if population == "data":
            pdata = {k: list(v) for k, v in mframe.items()}
            pop_terms = None
        elif population == "factorial":
            pdata = _yates_factorial_pop(mframe, terms, x2indx, xlevels)
            pop_terms = pdata.pop("_terms", None)
        elif population == "sas":
            if all(iscat.get(n, False) for n, flag in x2indx.items() if flag):
                pdata = _yates_factorial_pop(mframe, terms, x2indx, xlevels)
                pop_terms = pdata.pop("_terms", None)
            elif not any(iscat.get(n, False) for n, flag in x2indx.items() if flag):
                pdata = {k: list(v) for k, v in mframe.items()}
                pop_terms = None
            else:
                raise YatesError("mixed sas population not implemented")
        else:
            raise YatesError("unknown population")
    else:
        pdata = population
        pop_terms = None

    level_rows = contr["levels"]
    x1name = [name for name, flag in x1indx.items() if flag]
    x1data = [{k: row[k] for k in termname} for row in level_rows]

    xmatlist: list[np.ndarray] = []
    pdata_names = list(_frame_to_dict(pdata).keys())
    np_rows = len(next(iter(_frame_to_dict(pdata).values())))

    if pop_terms is None:
        kdrop = [i for i, name in enumerate(pdata_names) if name in x1name]
        base = {name: pdata[name] for i, name in enumerate(pdata_names) if i not in kdrop}
        for _i, x1row in enumerate(x1data):
            tdata = {k: list(v) for k, v in base.items()}
            for name in x1name:
                tdata[name] = [x1row.get(name, x1row.get(termname[x1name.index(name)]))] * np_rows
            tdata[terms.response] = [0.0] * np_rows
            x, _, _a = model_matrix(terms, tdata, xlevels=xlevels, contrasts=contrasts)
            xmatlist.append(x)
    else:
        base = _frame_to_dict(pdata)
        for x1row in x1data:
            tdata = {k: list(v) for k, v in base.items()}
            for name in x1row:
                tdata[name] = [x1row[name]] * np_rows
            tdata[terms.response] = [0.0] * np_rows
            x, _, _a = model_matrix(terms, tdata, xlevels=xlevels, contrasts=contrasts)
            xmatlist.append(x)
    return xmatlist


@dataclass
class YatesResult:
    estimate: dict[str, Any]
    test: np.ndarray
    mvar: np.ndarray | None
    cmat: np.ndarray | None = None
    call: Any = None
    class_: str = "yates"
    summary: Any = None
    pmm: Any = None
    mvar2: Any = None
    SAS: Any = None


def yates(
    fit: Any,
    term: Any,
    population: str | dict[str, Any] = "data",
    levels: Any = None,
    test: str = "global",
    predict: str = "linear",
    options: Any = None,
    nsim: int = 200,
    method: str = "direct",
) -> YatesResult:
    fitd = _as_dict(fit)
    if "terms" not in fitd:
        raise YatesError("the fit does not have a terms structure")
    terms = fitd["terms"]
    if not isinstance(terms, Terms):
        raise YatesError("the fit does not have a terms structure")

    if _fit_class(fitd) == "coxphms":
        raise YatesError("multi-state coxph not yet supported")
    if isinstance(predict, (list, dict)) or callable(predict):
        raise YatesError("user written prediction functions are not yet supported")

    mfun = _yates_setup_inline(fitd, predict, options)
    if mfun is None:
        predict = "linear"

    mframe = fitd.get("model")
    if mframe is None:
        raise YatesError("model frame is missing from fit")
    xold, _xn, _ = model_matrix(terms, {**mframe, terms.response: mframe[terms.response]}, xlevels=fitd.get("xlevels"))
    xassign = fitd.get("assign")
    if xassign is None:
        _, _, xassign = model_matrix(terms, mframe, xlevels=fitd.get("xlevels"))

    tatt = _terms_attributes(terms)
    termname = terms.variables[1:]
    iscat = {name: tatt["dataClasses"][name] in {"character", "factor"} for name in termname}

    method = _match_arg(method.lower(), ["direct", "sgtt"])
    if method == "sgtt" and population == "data":
        population = "sas"

    if isinstance(population, dict) and not isinstance(population, str):
        popframe = True
    elif isinstance(population, str):
        popframe = False
        population = _match_arg(population.lower(), ["data", "factorial", "sas", "empirical", "yates"])
        if population == "empirical":
            population = "data"
        if population == "yates":
            population = "factorial"
    else:
        raise YatesError("the population argument must be a data frame or character")

    test = _match_arg(test, ["global", "trend", "pairwise"])

    if method == "sgtt" and (population != "sas" or predict != "linear"):
        raise YatesError("sgtt method only applies if population = sas and predict = linear")

    coef_names = fitd.get("coef_names") or list(fitd.get("coefficients", {}).keys())
    beta = np.array([fitd["coefficients"][n] for n in coef_names], dtype=float)
    nabeta = np.isnan(beta)
    vmat = np.asarray(fitd["vcov"], dtype=float)
    if vmat.shape[0] > int(np.sum(~nabeta)):
        vmat = vmat[~nabeta][:, ~nabeta]

    sigma = fitd.get("sigma") if _fit_class(fitd) == "lm" else None

    contr = _cmatrix(fitd, term, test=test, levels=levels, assign=xassign)
    x1data = contr["levels"]

    xmatlist = _yates_xmat(terms, tatt, contr, population, mframe, fitd, iscat)

    estimable = np.ones(len(xmatlist), dtype=bool)
    if np.any(nabeta) and (popframe or population != "none"):
        xu = np.unique(xold, axis=0)
        if _fit_class(fitd) == "coxph":
            q, _r = np.linalg.qr(np.vstack([np.ones(len(xu)), xu]).T)
        else:
            q, _r = np.linalg.qr(xu.T)
        eps = math.sqrt(np.finfo(float).eps)

        def _estimcheck(x: np.ndarray) -> bool:
            temp = np.abs(x.T - q @ (q.T @ x.T))
            return bool(np.all(temp < eps))

        estimable = np.array([_estimcheck(x) for x in xmatlist], dtype=bool)

    beta_fit = beta[~nabeta]
    if predict == "linear" or mfun is None:
        weight = None
        if not popframe and population == "data":
            weight = None  # weights/id not used in proof case

        def meanfun(x: np.ndarray) -> np.ndarray:
            if weight is None:
                return np.mean(x, axis=0)
            w = np.asarray(weight, dtype=float)
            return np.sum(x * w[:, None], axis=0) / np.sum(w)

        cmat = np.vstack([meanfun(x) for x in xmatlist])
        offset = 0.0
        if _fit_class(fitd) == "coxph":
            means = np.asarray(fitd["means"], dtype=float)
            nkeep = len(means)
            cols = np.arange(cmat.shape[1])[:: max(1, cmat.shape[1] // nkeep)][:nkeep]
            cmat = cmat[:, cols]
            offset = -float(np.sum(means[~nabeta] * beta_fit))
        else:
            cmat = cmat[:, ~nabeta]

        level_key = contr["termname"][0]
        estimate = {
            level_key: [row[level_key] for row in x1data],
            "pmm": np.full(len(x1data), np.nan),
            "std": np.full(len(x1data), np.nan),
        }
        etemp = None
        if np.any(estimable):
            etemp = _estfun(cmat[estimable, :], beta_fit, vmat)
            estimate["pmm"][estimable] = etemp["estimate"] + offset
            estimate["std"][estimable] = np.sqrt(np.diag(etemp["var"]))

        if method == "sgtt":
            raise YatesError("sgtt method not implemented")
        if isinstance(contr["cmat"], dict):
            tests = []
            names = []
            for name, mat in contr["cmat"].items():
                tests.append(_testfun(np.asarray(mat, dtype=float) @ cmat, beta_fit, vmat, sigma**2 if sigma else None))
                names.append(name)
            test_mat = np.array([[t["chisq"], t["df"], t.get("ss", np.nan)] for t in tests])
        else:
            mat = np.asarray(contr["cmat"], dtype=float)
            t0 = _testfun(mat @ cmat, beta_fit, vmat, sigma**2 if sigma else None)
            test_mat = np.array([[t0["chisq"], t0["df"], t0.get("ss", np.nan)]])

        if etemp is not None and np.any(estimable):
            result = YatesResult(
                estimate=estimate,
                test=test_mat,
                mvar=etemp["var"],
                cmat=cmat,
                call=inspect.currentframe().f_back,
            )
        else:
            result = YatesResult(estimate=estimate, test=test_mat, mvar=None, cmat=cmat, call=None)
    else:
        raise YatesError("nonlinear prediction path not implemented")

    return result


def _yates_setup_inline(fit: dict[str, Any], predict: str, options: Any) -> None:
    klass = _fit_class(fitd := fit)
    if klass == "glm":
        if predict in {"link", "linear"}:
            return None
        if predict == "response":
            raise YatesError("response prediction not implemented")
        if predict == "terms":
            raise YatesError("type terms not yet supported")
    if klass == "coxph":
        if predict in {"lp", "linear"}:
            return None
        raise YatesError("type expected is not supported")
    if predict not in {"linear", "link"} and klass not in {"lm", "glm", "coxph"}:
        return None
    return None


__all__ = ["yates", "lm_fit", "YatesResult"]
