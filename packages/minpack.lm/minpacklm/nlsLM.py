"""Nonlinear least squares through :func:`minpacklm.nls_lm.nls_lm`."""

from __future__ import annotations

import re

import numpy as np

from minpacklm.nls_lm import nls_lm
from minpacklm.nls_lm_control import nls_lm_control

_NAME = re.compile(r"[A-Za-z.][A-Za-z0-9._]*")
_DIGITS = max(3, 7 - 3)
_FUNCS = {
    "exp": np.exp,
    "expm1": np.expm1,
    "log": np.log,
    "log10": np.log10,
    "log1p": np.log1p,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "pi": np.pi,
}


def nlsLM(
    formula,
    data=None,
    start=None,
    jac=None,
    algorithm="LM",
    control=None,
    lower=None,
    upper=None,
    trace=False,
    subset=None,
    weights=None,
    na_action="omit",
    model=False,
    **kwargs,
):
    """Fit ``formula`` by Levenberg-Marquardt, as ``nlsLM`` does.

    ``data`` is a mapping of column names to arrays. ``start`` is a mapping of
    parameter names to numbers. A ``^`` in the formula is the power operator.
    """
    if start is None:
        raise ValueError("parameters without starting value in 'data': pass start")
    if data is None:
        data = {}
    text = str(formula).strip()
    if "~" not in text:
        raise ValueError("formula must contain '~'")
    lhs_text, rhs_text = text.split("~", 1)
    lhs_text = lhs_text.strip() or "0"
    rhs_text = rhs_text.strip()
    names = _start_items(start)
    columns = _columns(data)
    if subset is not None:
        columns, weights = _apply_subset(columns, weights, subset)
    weights = _coerce_weights(weights, formula=text, data=columns, start=names)
    lhs = _eval(lhs_text, _namespace(columns, names))
    lhs = np.asarray(lhs, dtype=float).reshape(-1)
    n_obs = int(lhs.size)
    columns = _align(columns, n_obs)
    if weights is not None:
        weights = np.asarray(weights, dtype=float).reshape(-1)
        if weights.size == 1 and n_obs != 1:
            weights = np.repeat(weights, n_obs)
        if weights.size != n_obs:
            raise ValueError("weights must have one value per observation")
        if np.any(np.isnan(weights) | (weights < 0)):
            raise ValueError("missing or negative weights not allowed")
    used = [name for name in _names(lhs_text + " " + rhs_text) if name not in names and name not in _FUNCS]
    if na_action == "omit":
        keep = np.ones(n_obs, dtype=bool)
        if np.any(~np.isfinite(lhs)):
            keep &= np.isfinite(lhs)
        for name in used:
            if name in columns and columns[name].size == n_obs:
                keep &= np.isfinite(columns[name])
        if weights is not None:
            keep &= np.isfinite(weights)
        if not np.all(keep):
            lhs = lhs[keep]
            columns = {
                name: (values[keep] if values.size == n_obs else values)
                for name, values in columns.items()
            }
            if weights is not None:
                weights = weights[keep]
            n_obs = int(lhs.size)
    elif na_action not in (None, "none", "fail"):
        raise ValueError("na_action must be 'omit', 'fail', or 'none'")
    if na_action == "fail":
        if not np.all(np.isfinite(lhs)):
            raise ValueError("missing values are not allowed")
    swts = np.ones(n_obs, dtype=float) if weights is None else np.sqrt(weights)
    order = list(names)

    def resid(par):
        current = {name: float(par[index]) for index, name in enumerate(order)}
        rhs = _eval(rhs_text, _namespace(columns, current))
        rhs = np.asarray(rhs, dtype=float).reshape(-1)
        return swts * (lhs - rhs)

    stored = _stored_control(control, trace)
    fit = nls_lm(
        np.array([float(names[name]) for name in order], dtype=float),
        resid,
        jac=jac,
        lower=lower,
        upper=upper,
        control=stored,
        **kwargs,
    )
    solved = np.asarray(fit["par"], dtype=float)
    solved_map = {name: float(solved[index]) for index, name in enumerate(order)}
    fitted = np.asarray(_eval(rhs_text, _namespace(columns, solved_map)), dtype=float).reshape(-1)
    response = lhs - fitted
    info = int(fit["info"])
    result = NlsLMResult(
        formula=text,
        coefficients={name: float(solved[index]) for index, name in enumerate(order)},
        residuals=response,
        fitted=fitted,
        deviance=float(fit["deviance"]),
        weights=None if weights is None else np.asarray(weights, dtype=float),
        conv_info={
            "isConv": info in (1, 2, 3, 4),
            "finIter": int(fit["niter"]),
            "finTol": float(nls_lm_control()["ftol"]),
            "stopCode": info,
            "stopMessage": str(fit["message"]),
        },
        control=stored,
        algorithm=algorithm,
        info=info,
        niter=int(fit["niter"]),
        message=str(fit["message"]),
        model=columns if model else None,
    )
    return result


class NlsLMResult:
    """Values ``nlsLM`` returns for coefficients, residuals, fitted values, and convergence."""

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def coef(self):
        return dict(self.coefficients)

    def __str__(self):
        names = list(self.coefficients)
        values = [self.coefficients[name] for name in names]
        weighted = self.weights is not None and float(np.max(self.weights) - np.min(self.weights)) != 0.0
        kind = "weighted residual" if weighted else "residual"
        deviance = format(float(self.deviance), f".{_DIGITS}g")
        info = self.conv_info
        title = "to convergence:" if info["isConv"] else "till stop:"
        tolerance = format(float(info["finTol"]), f".{_DIGITS}g")
        lines = [
            "Nonlinear regression model",
            f"  model: {self.formula}",
            "   data: data",
            _coef_block(names, values),
            f" {kind} sum-of-squares: {deviance}",
            "",
            f"Number of iterations {title} {info['finIter']} ",
            f"Achieved convergence tolerance: {tolerance}",
        ]
        if not info["isConv"]:
            lines.append(f"Reason stopped: {info['stopMessage']}")
        return "\n".join(lines) + "\n"


def _start_items(start):
    if isinstance(start, dict):
        return {name: float(value) for name, value in start.items()}
    if isinstance(start, np.ndarray) and start.dtype.names:
        return {name: float(start[name]) for name in start.dtype.names}
    raise TypeError("start must be a mapping of parameter names")


def _columns(data):
    columns = {}
    for name, values in data.items():
        columns[str(name)] = np.asarray(values, dtype=float).reshape(-1)
    return columns


def _apply_subset(columns, weights, subset):
    index = np.asarray(subset)
    if index.dtype == bool:
        mask = index
    else:
        mask = np.asarray(index, dtype=int) - 1
    out = {}
    for name, values in columns.items():
        out[name] = values[mask]
    if weights is not None and not hasattr(weights, "evaluate"):
        weights = np.asarray(weights, dtype=float).reshape(-1)[mask]
    return out, weights


def _coerce_weights(weights, formula, data, start):
    evaluate = getattr(weights, "evaluate", None)
    if evaluate is not None and getattr(weights, "expr", None) is not None:
        return np.asarray(
            evaluate(formula=formula, data=data, start=start),
            dtype=float,
        )
    return weights


def _names(text):
    return _NAME.findall(text)


def _py_expr(text):
    return re.sub(r"(?<!\*)\^(?!\*)", "**", text)


def _namespace(columns, parameters):
    env = dict(_FUNCS)
    for name, values in columns.items():
        env[name] = values
    for name, value in parameters.items():
        env[name] = value
    return env


def _eval(text, env):
    return eval(_py_expr(text), {"__builtins__": {}}, env)


def _align(columns, n_obs):
    aligned = {}
    for name, values in columns.items():
        if values.size == 1 and n_obs != 1:
            aligned[name] = np.repeat(values, n_obs)
        else:
            aligned[name] = values
    return aligned


def _stored_control(control, trace):
    stored = nls_lm_control()
    if control is not None:
        for key, value in dict(control).items():
            stored[key] = value
    if trace:
        stored["nprint"] = 1
    return stored


def _coef_block(names, values):
    cells = [format(float(value), ".8g") for value in values]
    width = max([len(cell) for cell in cells] + [len(name) for name in names])
    head = " ".join(name.rjust(width) for name in names)
    body = " ".join(cell.rjust(width) for cell in cells)
    return head + "\n" + body
