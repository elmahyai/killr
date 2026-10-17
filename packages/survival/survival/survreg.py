"""Formula wrapper for survreg (survival::survreg).

The formula is read with formulaic. model.frame's na.omit is formulaic's
``drop`` rule, applied after the response, weights, offset, and strata are
checked for missing values. model.matrix is formulaic's treatment coding, with
the same level order as R's sorted factor levels. ``strata()`` and ``offset()``
terms leave the design, as R's ``untangle.specials`` does.

Not translated here: ``robust`` and ``cluster`` (they need ``residuals.survreg``),
``model = TRUE`` (R's model frame object), penalized terms (``frailty``,
``ridge``, ``pspline``), start-stop and multi-state responses, and the R
``terms`` object. A distribution that needs the R density callback raises
``NotImplementedError`` from ``survreg_fit``.

``subset`` takes a boolean array or 1-based integer positions. ``weights`` and
``offset`` take a column name or an array aligned to the data rows.
"""

from __future__ import annotations

import ast
import re
import warnings
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd
from formulaic import Formula, model_matrix

from survival.control import survreg_control
from survival.surv import Surv
from survival.survreg_distributions import survreg_distributions
from survival.survreg_dtest import survregDtest
from survival.survreg_fit import survreg_fit

_CONTEXT = {"log": np.log, "exp": np.exp, "sqrt": np.sqrt}
_IDENT = re.compile(r"[A-Za-z_.][A-Za-z0-9_.]*")
_PENALTY = re.compile(r"(frailty|ridge|pspline)\(")
_SPECIAL = re.compile(r"(strata|offset|cluster|frailty|ridge|pspline)\(")
# R's list spells this name "Log logisit", so the log-logistic distribution
# is not in the fix list. The spelling is kept on purpose.
_FIX_NAMES = ("Weibull", "Exponential", "Rayleigh", "Log Normal", "Log logisit")


def _as_frame(data: Any) -> pd.DataFrame:
    if data is None:
        raise ValueError("a data argument is required")
    if isinstance(data, pd.DataFrame):
        return data.reset_index(drop=True)
    return pd.DataFrame(dict(data))


def _call_parts(text: str, what: str):
    """Split a call such as ``Surv(time, status)`` into name, argument sources, and keywords."""
    node = ast.parse(text.strip(), mode="eval").body
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise ValueError(f"{what} must be a call, got {text!r}")
    args = [ast.get_source_segment(text, arg) for arg in node.args]
    keywords = {kw.arg: kw.value for kw in node.keywords}
    return node.func.id, args, keywords


def _split_formula(formula: str):
    """Return the response text, the plain rhs terms, strata and offset arguments, and intercept."""
    spec = Formula(formula)
    lhs = str(spec.lhs) if spec.lhs is not None else ""
    if not lhs:
        raise ValueError("Response must be a survival object")
    intercept = False
    plain: list[str] = []
    strata_args: list[str] = []
    offset_args: list[str] = []
    for term in (str(item) for item in spec.rhs):
        if term == "1":
            intercept = True
            continue
        if _PENALTY.match(term):
            raise NotImplementedError(f"{term[:-1]} is a penalized term; survpenal.fit is not translated")
        if term.startswith("cluster("):
            raise NotImplementedError("cluster() needs the robust variance, which is not translated")
        if term.startswith("strata("):
            _, args, keywords = _call_parts(term, "strata term")
            extra = set(keywords) - {"shortlabel"}
            if extra:
                raise NotImplementedError(f"strata argument {sorted(extra)} is not translated")
            strata_args.extend(args)
        elif term.startswith("offset("):
            _, args, _ = _call_parts(term, "offset term")
            if len(args) != 1:
                raise ValueError("offset() takes one argument")
            offset_args.extend(args)
        else:
            if _SPECIAL.search(term):
                raise NotImplementedError(f"special term {term!r} inside another term is not translated")
            plain.append(term)
    return lhs, plain, strata_args, offset_args, intercept


def _surv_parts(lhs: str):
    name, args, keywords = _call_parts(lhs, "response")
    if name != "Surv":
        raise ValueError("Response must be a survival object")
    if not args:
        raise ValueError("Surv needs a time argument")
    kwargs: dict[str, Any] = {}
    for key, node in keywords.items():
        if key != "type":
            raise NotImplementedError(f"Surv argument {key!r} is not translated")
        kwargs["type"] = ast.literal_eval(node)
    return args, kwargs


def _value(expr: str, data: pd.DataFrame) -> np.ndarray:
    """One model-frame variable: a column, or a formulaic expression with one column."""
    expr = expr.strip()
    if _IDENT.fullmatch(expr) and expr in data.columns:
        return data[expr].to_numpy()
    mm = model_matrix("0 + " + expr, data, na_action="ignore", context=_CONTEXT)
    if mm.shape[1] != 1:
        raise ValueError(f"{expr!r} must give one column")
    return mm.iloc[:, 0].to_numpy()


def _positions(subset: Any, n: int) -> np.ndarray:
    if subset is None:
        return np.arange(n)
    arr = np.asarray(subset)
    if arr.dtype == bool:
        if arr.shape[0] != n:
            raise ValueError("subset has the wrong length")
        return np.flatnonzero(arr)
    return arr.astype(int) - 1


def _distribution(dist: Any):
    """Return the distribution name and list, with R's partial matching of names."""
    if isinstance(dist, str):
        if dist in survreg_distributions:
            name = dist
        else:
            hits = [key for key in survreg_distributions if key.startswith(dist)]
            if len(hits) != 1:
                names = ", ".join(repr(key) for key in survreg_distributions)
                raise ValueError(f"'arg' should be one of {names}")
            name = hits[0]
        return name, survreg_distributions[name]
    if isinstance(dist, Mapping):
        dlist = dict(dist)
        return dlist.get("name"), dlist
    raise ValueError("Invalid distribution object")


def _parms(dlist: Mapping[str, Any], parms: Any):
    """The parms list of a distribution, with user values in place (R's survreg parms block)."""
    default = dlist.get("parms")
    if default is None:
        if parms is not None:
            raise ValueError(f"{dlist.get('name')} distribution has no optional parameters")
        return None
    if not isinstance(default, Mapping):
        raise ValueError("Default parameters must be a numeric vector")
    out = dict(default)
    if parms is not None:
        if isinstance(parms, Mapping):
            if any(key not in out for key in parms):
                raise ValueError("Invalid parameter names")
            out.update(parms)
        else:
            values = np.atleast_1d(np.asarray(parms, dtype=float))
            for key, value in zip(list(out), values):
                out[key] = float(value)
    return out


def survreg(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action="omit",
    dist="weibull",
    init=None,
    scale=0,
    control=None,
    parms=None,
    model=False,
    x=False,
    y=True,
    robust=False,
    cluster=None,
    score=False,
    **control_args,
):
    """Fit a parametric survival model (survival::survreg).

    ``formula`` is a string such as ``"Surv(time, status) ~ x + g"``. The
    returned dict uses the R field names: ``coefficients``, ``icoef``, ``var``,
    ``loglik``, ``iter``, ``linear.predictors``, ``scale``, ``idf``, ``df``,
    ``df.residual``, ``means``, ``dist``, and ``n``. ``y`` and ``x`` are
    returned when requested, and so are ``score``, ``parms``, ``xlevels`` and
    ``contrasts`` for factors, and ``na.action`` (0-based omitted rows of
    ``data``) when rows were dropped.
    """
    if formula is None:
        raise ValueError("a formula argument is required")
    if na_action != "omit":
        raise NotImplementedError("only na.action = 'omit' is translated")
    if model:
        raise NotImplementedError("model = TRUE returns R's model frame, which is not translated")
    if robust or cluster is not None:
        raise NotImplementedError("robust and cluster variances need residuals.survreg, which is not translated")

    frame = _as_frame(data)
    lhs, plain, strata_args, offset_args, intercept = _split_formula(str(formula))
    base = _positions(subset, len(frame))
    frame1 = frame.iloc[base].reset_index(drop=True)
    n1 = base.size

    # Response. Surv is called with the evaluated arguments.
    surv_args, surv_kwargs = _surv_parts(lhs)
    surv = Surv(*[_value(arg, frame1) for arg in surv_args], **surv_kwargs)
    if surv.type == "counting":
        raise ValueError("start-stop type Surv objects are not supported")
    if surv.type in ("mright", "mcounting"):
        raise ValueError("multi-state survival is not supported")

    # na.omit: a row is kept when the response, weights, offset, strata, and
    # the model matrix columns are all present.
    keep = ~np.any(np.isnan(surv.columns), axis=1)

    weight_values = None
    if weights is not None:
        if isinstance(weights, str):
            weight_values = frame1[weights].to_numpy(dtype=float)
        else:
            weight_values = np.asarray(weights, dtype=float)[base]
        keep &= ~np.isnan(weight_values)

    offset_values = np.zeros(n1)
    if offset_args:
        offset_values = sum(np.asarray(_value(arg, frame1), dtype=float) for arg in offset_args)
        keep &= ~np.isnan(offset_values)

    strata_codes = None
    if strata_args:
        # Level codes are sorted, as R's factor() gives them. With several
        # variables the groups are the sorted tuples of level codes, first
        # variable most significant, and only tuples present in the data count.
        level_codes = []
        for arg in strata_args:
            codes, _ = pd.factorize(_value(arg, frame1), sort=True)
            level_codes.append(codes.astype(float))
        mat = np.column_stack(level_codes)
        good = ~np.any(mat < 0, axis=1)
        strata_codes = np.full(n1, np.nan)
        if good.any():
            _, inverse = np.unique(mat[good].astype(np.int64), axis=0, return_inverse=True)
            strata_codes[good] = np.asarray(inverse).reshape(-1) + 1.0
        keep &= ~np.isnan(strata_codes)

    rhs = ("1" if intercept else "0") + "".join(f" + {term}" for term in plain)
    mm_rows = model_matrix(rhs, frame1, na_action="drop", context=_CONTEXT)
    keep_rhs = np.zeros(n1, dtype=bool)
    keep_rhs[np.asarray(mm_rows.index, dtype=int)] = True
    keep &= keep_rhs

    rows = np.flatnonzero(keep)
    omitted = base[np.flatnonzero(~keep)]
    frame2 = frame1.iloc[rows].reset_index(drop=True)
    n = rows.size

    # Design matrix and response on the kept rows.
    X = np.asarray(model_matrix(rhs, frame2, na_action="drop", context=_CONTEXT), dtype=float)
    if X.shape[0] != n:
        raise RuntimeError("model matrix rows do not match the model frame")
    if not np.all(np.isfinite(X)):
        raise ValueError("data contains an infinite predictor")
    Y = surv.columns[rows].copy()
    weights_out = weight_values[rows] if weight_values is not None else None
    off = offset_values[rows] if offset_args else np.zeros(n)
    strata_arr = None
    nstrata = 1
    if strata_codes is not None:
        strata_arr = strata_codes[rows].astype(np.int32)
        nstrata = int(strata_arr.max())

    # Distribution, as survreg() does it.
    dist_name, dlist = _distribution(dist)
    if not survregDtest(dlist):
        raise ValueError("Invalid distribution object")

    type_ = surv.type
    if type_ == "interval" and dlist.get("name") in _FIX_NAMES:
        fix = (Y[:, 0] == 0) & (Y[:, 2] == 3)
        if fix.any():
            count = int(fix.sum())
            Y[fix] = np.column_stack([Y[fix, 1], np.ones(count), np.full(count, 2.0)])
    y_save = Y.copy()

    logcorrect = 0.0
    trans = dlist.get("trans")
    if trans is not None:
        dtrans = dlist["dtrans"]
        exact = Y[:, -1] == 1
        if exact.any():
            contrib = np.log(dtrans(Y[exact, 0]))
            if weights_out is None:
                logcorrect = float(np.sum(contrib))
            else:
                logcorrect = float(np.sum(weights_out[exact] * contrib))
        if type_ == "interval":
            if np.any(Y[:, 2] == 3):
                Y = np.column_stack([trans(Y[:, :2]), Y[:, 2]])
            else:
                Y = np.column_stack([trans(Y[:, 0]), Y[:, 2]])
        elif type_ == "left":
            Y = np.column_stack([trans(Y[:, 0]), 2 - Y[:, 1]])
        else:
            Y = np.column_stack([trans(Y[:, 0]), Y[:, 1]])
        if not np.all(np.isfinite(Y)):
            raise ValueError("Invalid survival times for this distribution")
    else:
        if type_ == "left":
            Y[:, 1] = 2 - Y[:, 1]
        elif type_ == "interval" and np.all(Y[:, 2] < 3):
            Y = Y[:, [0, 2]]

    if dlist.get("scale") is not None:
        if scale != 0:
            warnings.warn(f"{dlist.get('name')} has a fixed scale, user specified value ignored")
        scale = dlist["scale"]
    if dlist.get("dist") is not None:
        target = dlist["dist"]
        dlist = survreg_distributions[target] if isinstance(target, str) else dict(target)

    parms_out = _parms(dlist, parms)

    if control is None:
        ctrl = survreg_control(**control_args)
    elif isinstance(control, Mapping):
        ctrl = survreg_control(**{key.replace(".", "_"): value for key, value in control.items()})
    else:
        raise ValueError("control must be a mapping")

    scale = float(scale)
    if scale < 0:
        raise ValueError("Invalid scale value")
    if scale > 0 and nstrata > 1:
        raise ValueError("The scale argument is not valid with multiple strata")

    fit = survreg_fit(
        X,
        Y,
        weights=weights_out,
        offset=off,
        init=init,
        controlvals=ctrl,
        dist=dlist,
        scale=scale,
        nstrat=nstrata,
        strata=strata_arr,
        parms=parms_out,
    )

    coef = np.asarray(fit["coefficients"], dtype=float)
    var = np.asarray(fit["var"], dtype=float)
    if scale == 0:
        nvar = coef.size - nstrata
        scale_out = np.exp(coef[nvar:])
        coef = coef[:nvar]
        idf = 1 + nstrata
    else:
        scale_out = scale
        idf = 1
    loglik = np.asarray(fit["loglik"], dtype=float) + logcorrect
    singular = np.diag(var)[: coef.size] == 0
    coef = np.where(singular, np.nan, coef)

    result: dict[str, Any] = {
        "coefficients": coef,
        "icoef": np.asarray(fit["icoef"], dtype=float),
        "var": var,
        "loglik": loglik,
        "iter": fit["iter"],
        "linear.predictors": np.asarray(fit["linear.predictors"], dtype=float),
        "scale": scale_out,
        "idf": idf,
        "df": fit["df"],
        "df.residual": n - fit["df"],
        "means": X.mean(axis=0),
        "dist": dist_name,
        "n": n,
    }
    if weights_out is not None:
        result["weights"] = weights_out
    if y:
        result["y"] = y_save
    if x:
        result["x"] = X
    if score:
        result["score"] = fit["score"]
    if parms_out:
        result["parms"] = parms_out

    xlevels: dict[str, list[str]] = {}
    contrasts: dict[str, str] = {}
    for term in plain:
        if _IDENT.fullmatch(term) and term in frame2.columns:
            column = frame2[term]
            if isinstance(column.dtype, pd.CategoricalDtype):
                levels = [str(v) for v in column.cat.categories]
            elif pd.api.types.is_string_dtype(column):
                levels = sorted({str(v) for v in column.dropna()})
            else:
                continue
            xlevels[term] = levels
            contrasts[term] = "contr.treatment"
    if xlevels:
        result["xlevels"] = xlevels
        result["contrasts"] = contrasts
    if omitted.size:
        result["na.action"] = omitted
    return result
