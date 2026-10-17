"""Fit a nonlinear model by generalized least squares (nlme ``gnls``).

The coefficient step is ``fit_gnls``. With no correlation and no variance
function the algorithm takes that step and stops, which is the path proved
against R. A correlation structure or a variance function needs the alternating
GLS update, which is not in this module.
"""

from __future__ import annotations

import inspect
import math
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from nlme.gnlscontrol import gnlsControl
from nlme.gnlsstruct import GnlsStruct, gnlsStruct
from nlme.varfunc import varFunc

try:
    import gnlsfit
except ImportError:  # pragma: no cover - installed with the crate
    gnlsfit = None

_FUNCTIONS = {"exp": np.exp, "log": np.log, "sqrt": np.sqrt, "abs": np.abs, "sin": np.sin, "cos": np.cos}
_STEP_HALVING = "step halving factor reduced below minimum in NLS step"
_NO_CONVERGENCE = "maximum number of iterations reached without convergence"


@dataclass
class Gnls:
    """Fitted ``gnls`` object, also marked as ``gls`` the way R classes it."""

    coefficients: np.ndarray
    names: tuple[str, ...]
    sigma: float
    logLik: float
    numIter: int
    fitted: np.ndarray
    residuals: np.ndarray
    varBeta: np.ndarray
    dims: dict[str, Any]
    formula: str
    modelStruct: GnlsStruct
    apVar: Any = None
    method: str = "ML"
    groups: Any = None
    contrasts: dict[str, Any] = field(default_factory=dict)
    std: np.ndarray | None = None
    plist: dict[str, Any] = field(default_factory=dict)
    pmap: dict[str, int] = field(default_factory=dict)
    parAssign: dict[str, list[int]] = field(default_factory=dict)
    fixedSigma: bool = False
    classes: tuple[str, ...] = ("gnls", "gls")


def gnls(
    model: str,
    data: Any = None,
    params: Any = None,
    start: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    na_action: Any = None,
    naPattern: Any = None,
    control: Any = None,
    verbose: bool = False,
) -> Gnls:
    """Fit ``model`` by generalized nonlinear least squares.

    ``model`` is ``"response ~ mean"``. ``start`` is a dict of initial
    coefficients, or a numeric sequence when ``params`` names them. Each
    parameter is constant across observations. ``data`` is a column mapping;
    omitted, the caller's variables are used.
    """
    if correlation is not None or weights is not None:
        raise NotImplementedError(
            "gnls with correlation or weights is waiting on the alternating GLS step"
        )
    if naPattern is not None:
        raise NotImplementedError("gnls naPattern is not translated")
    if na_action not in (None, "na.fail"):
        raise NotImplementedError("gnls na.action other than na.fail is not translated")
    if gnlsfit is None:
        raise ImportError("gnlsfit extension is required for gnls")

    lhs_text, rhs_text = _split_model(model)
    names, spar = _starting_values(start, params)
    if params is not None:
        names = _param_names(params, names)
        if spar.size != len(names):
            raise ValueError(
                f"supplied {spar.size} starting values, need {len(names)}"
            )
    lhs = _parse(lhs_text)
    rhs = _parse(rhs_text)
    if data is None:
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        if caller is None:
            raise ValueError("data must be given")
        data = {**caller.f_globals, **caller.f_locals}
    columns = _model_frame(data, _needed_columns(lhs, rhs, names), subset)
    n = int(next(iter(columns.values())).shape[0])
    p = len(names)
    if n <= p:
        raise ValueError("need more observations than parameters")
    for column in columns.values():
        if np.isnan(column).any():
            raise ValueError("missing values in object")

    controlvals = gnlsControl()
    if control:
        for key, value in dict(control).items():
            controlvals[key] = value

    gnls_st = gnlsStruct(corStruct=correlation, varStruct=varFunc(weights))
    fixed_sigma = float(controlvals["sigma"]) > 0.0
    plist = {name: True for name in names}
    pmap = {name: index for index, name in enumerate(names)}
    par_assign = {name: [index + 1] for index, name in enumerate(names)}
    beta = np.array(spar, dtype=np.float64, copy=True)

    def flat(theta: np.ndarray) -> np.ndarray:
        return _design_and_residual(columns, names, theta, lhs, rhs)

    def callback(theta_list: list[float]) -> list[float]:
        theta = np.asarray(theta_list, dtype=np.float64)
        beta[:] = theta
        return flat(theta).tolist()

    num_iter = 0
    nls_settings = [
        float(controlvals["nlsMaxIter"]),
        float(controlvals["minScale"]),
        float(controlvals["nlsTol"]),
        0.0,
        0.0,
        0.0,
    ]
    while True:
        num_iter += 1
        theta, nls_settings, _additional = gnlsfit.fit_gnls(
            beta.tolist(),
            [p, n, 0],
            [1.0],
            [1.0],
            [1],
            nls_settings,
            [0.0] * n,
            0,
            0,
            callback,
        )
        theta_arr = np.asarray(theta, dtype=np.float64)
        if float(nls_settings[3]) == 1.0:
            if controlvals["returnObject"]:
                warnings.warn(_STEP_HALVING, stacklevel=2)
                break
            raise RuntimeError(_STEP_HALVING)
        old = np.array(spar, dtype=np.float64, copy=True)
        spar[:] = theta_arr
        beta[:] = theta_arr
        if float(nls_settings[4]) < float(controlvals["nlsMaxIter"]):
            break
        denom = np.where(np.abs(spar) < float(controlvals["tolerance"]), 1.0, spar)
        conv = float(np.max(np.abs((old - spar) / denom)))
        if verbose:
            print(f"NLS step: RSS = {nls_settings[5]} convergence {conv}")
        if conv <= float(controlvals["tolerance"]):
            break
        if num_iter >= float(controlvals["maxIter"]):
            if controlvals["returnObject"]:
                warnings.warn(_NO_CONVERGENCE, stacklevel=2)
                break
            raise RuntimeError(_NO_CONVERGENCE)

    packed = flat(beta)
    resid = packed[n * p :]
    design = packed[: n * p].reshape((n, p), order="F")
    sigma_control = float(controlvals["sigma"])
    rss = float(np.dot(resid, resid))
    if sigma_control == 0.0:
        sigma = math.sqrt(rss / (n - p))
        lsig = math.log(sigma) + 0.5 * math.log(1.0 - p / n)
        loglik = (-n * (1.0 + math.log(2.0 * math.pi) + 2.0 * lsig)) / 2.0
    else:
        sigma = sigma_control
        lsig = math.log(sigma)
        loglik = -(n * (math.log(2.0 * math.pi) / 2.0 + lsig) + rss / (2.0 * sigma * sigma))
    if sigma_control:
        sigma = sigma_control
    var_beta = _var_beta(design, sigma, names)
    y = _eval(lhs, {**columns, **_parameter_columns(names, beta, n)})
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    fitted = y - resid
    std = np.full(n, sigma, dtype=np.float64)
    if controlvals["apVar"]:
        ap_var = None
    else:
        ap_var = "Approximate variance-covariance matrix not available"
    return Gnls(
        coefficients=np.array(spar, dtype=np.float64, copy=True),
        names=tuple(names),
        sigma=float(sigma),
        logLik=float(loglik),
        numIter=int(num_iter),
        fitted=np.array(fitted, dtype=np.float64, copy=True),
        residuals=np.array(resid, dtype=np.float64, copy=True),
        varBeta=var_beta,
        dims={"p": p, "N": n, "REML": False},
        formula=model,
        modelStruct=gnls_st,
        apVar=ap_var,
        contrasts={},
        std=std,
        plist=plist,
        pmap=pmap,
        parAssign=par_assign,
        fixedSigma=fixed_sigma,
    )


def _split_model(model: str) -> tuple[str, str]:
    text = str(model).strip()
    if "~" not in text:
        raise ValueError('model formula must be of the form "resp ~ pred"')
    lhs, rhs = text.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    if not lhs or not rhs or "~" in rhs:
        raise ValueError('model formula must be of the form "resp ~ pred"')
    return lhs, rhs


def _starting_values(start: Any, params: Any) -> tuple[list[str], np.ndarray]:
    if start is None:
        raise ValueError("no initial values for model parameters")
    if isinstance(start, dict):
        names = [str(name) for name in start]
        values = np.array([float(start[name]) for name in start], dtype=np.float64)
        return names, values
    values = np.asarray(start, dtype=np.float64).reshape(-1)
    if params is None:
        raise ValueError("starting estimates must have names when 'params' is missing")
    return [], values


def _param_names(params: Any, start_names: list[str]) -> list[str]:
    if isinstance(params, str):
        texts = [params]
    elif isinstance(params, (list, tuple)):
        texts = [str(item) for item in params]
    else:
        raise ValueError("'params' must be a formula or list of formulae")
    names: list[str] = []
    for text in texts:
        if "~" not in text:
            raise ValueError('formulae in \'params\' must be of the form "parameter ~ expr"')
        left, right = text.split("~", 1)
        left = left.strip()
        right = right.strip()
        if right not in {"1", "1L"}:
            raise NotImplementedError("gnls params with a non-constant right-hand side are not translated")
        parts = [part.strip() for part in left.replace("+", " ").split() if part.strip()]
        if not parts:
            raise ValueError('formulae in \'params\' must be of the form "parameter ~ expr"')
        names.extend(parts)
    if start_names and names != start_names and len(names) != len(start_names):
        pass
    return names


def _needed_columns(lhs: tuple, rhs: tuple, parameters: list[str]) -> list[str]:
    skip = set(parameters) | {"pi"} | set(_FUNCTIONS)
    found: list[str] = []
    for node in (lhs, rhs):
        for name in _identifiers(node):
            if name not in skip and name not in found:
                found.append(name)
    return found


def _model_frame(data: Any, columns: list[str], subset: Any) -> dict[str, np.ndarray]:
    source = _column_source(data)
    frame: dict[str, np.ndarray] = {}
    for name in columns:
        if name not in source:
            raise ValueError(f"object '{name}' not found")
        values = np.asarray(source[name], dtype=np.float64).reshape(-1)
        frame[name] = values
    if not frame:
        raise ValueError("model has no data columns")
    length = frame[columns[0]].shape[0]
    for name, values in frame.items():
        if values.shape[0] != length:
            raise ValueError(f"column '{name}' has a different number of rows")
    if subset is None:
        return frame
    mask = np.asarray(subset)
    if mask.dtype == bool:
        return {name: values[mask] for name, values in frame.items()}
    index = np.asarray(mask, dtype=int)
    return {name: values[index] for name, values in frame.items()}


def _column_source(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    columns = getattr(data, "columns", None)
    if columns is not None and hasattr(data, "to_dict"):
        converted = data.to_dict(as_series=False)
        if isinstance(converted, dict):
            return converted
    if hasattr(data, "__getitem__"):
        return data
    raise TypeError("data must be a column mapping")


def _parameter_columns(names: list[str], beta: np.ndarray, n: int) -> dict[str, np.ndarray]:
    return {name: np.full(n, float(beta[index]), dtype=np.float64) for index, name in enumerate(names)}


def _resid(columns: dict[str, np.ndarray], pars: dict[str, np.ndarray], lhs: tuple, rhs: tuple) -> np.ndarray:
    env = {"pi": math.pi}
    env.update(pars)
    env.update(columns)
    left = np.asarray(_eval(lhs, env), dtype=np.float64).reshape(-1)
    right = np.asarray(_eval(rhs, env), dtype=np.float64).reshape(-1)
    return left - right


def _design_and_residual(
    columns: dict[str, np.ndarray],
    names: list[str],
    beta: np.ndarray,
    lhs: tuple,
    rhs: tuple,
) -> np.ndarray:
    n = int(next(iter(columns.values())).shape[0])
    pars = _parameter_columns(names, beta, n)
    base = _resid(columns, pars, lhs, rhs)
    ssize = math.sqrt(sys.float_info.epsilon)
    design = np.zeros((n, len(names)), dtype=np.float64)
    for index, name in enumerate(names):
        pp = np.array(pars[name], dtype=np.float64, copy=True)
        diff = np.where(pp == 0.0, ssize, pp * ssize)
        trial = dict(pars)
        trial[name] = pp + diff
        design[:, index] = (base - _resid(columns, trial, lhs, rhs)) / diff
    packed = np.concatenate([design.reshape(-1, order="F"), base])
    return np.where(np.isnan(packed), 0.0, packed)


def _var_beta(design: np.ndarray, sigma: float, names: list[str]) -> np.ndarray:
    gram = design.T @ design
    rank = int(np.linalg.matrix_rank(design, tol=math.sqrt(sys.float_info.epsilon)))
    if rank < len(names):
        print("approximate covariance matrix for parameter estimates not of full rank")
        raise RuntimeError("approximate covariance matrix for parameter estimates not of full rank")
    return (sigma * sigma) * np.linalg.inv(gram)


def _identifiers(node: tuple) -> list[str]:
    kind = node[0]
    if kind == "name":
        return [node[1]]
    if kind == "call":
        names = []
        for arg in node[2]:
            names.extend(_identifiers(arg))
        return names
    if kind == "bin":
        return _identifiers(node[2]) + _identifiers(node[3])
    if kind == "neg":
        return _identifiers(node[1])
    return []


def _eval(node: tuple, env: dict[str, Any]) -> Any:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "name":
        if node[1] not in env:
            raise ValueError(f"object '{node[1]}' not found")
        return env[node[1]]
    if kind == "neg":
        return -np.asarray(_eval(node[1], env), dtype=np.float64)
    if kind == "call":
        fn = _FUNCTIONS.get(node[1])
        if fn is None:
            raise ValueError(f"function '{node[1]}' is not available in gnls model expressions")
        args = [_eval(arg, env) for arg in node[2]]
        return fn(*args)
    if kind == "bin":
        op = node[1]
        left = np.asarray(_eval(node[2], env), dtype=np.float64)
        right = np.asarray(_eval(node[3], env), dtype=np.float64)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "^":
            return left**right
        raise ValueError(f"operator '{op}' is not available in gnls model expressions")
    raise ValueError("invalid model expression")


def _parse(text: str) -> tuple:
    tokens = _tokenize(text)
    parser = _Parser(tokens)
    node = parser.expression()
    if parser.peek() is not None:
        raise ValueError(f"cannot parse model expression '{text}'")
    return node


def _tokenize(text: str) -> list[tuple]:
    tokens = []
    i = 0
    while i < len(text):
        char = text[i]
        if char.isspace():
            i += 1
            continue
        if char in "+-*/^(),":
            tokens.append((char, char))
            i += 1
            continue
        if char.isdigit() or (char == "." and i + 1 < len(text) and text[i + 1].isdigit()):
            j = i + 1
            while j < len(text) and (text[j].isdigit() or text[j] == "."):
                j += 1
            if j < len(text) and text[j] in "eE":
                k = j + 1
                if k < len(text) and text[k] in "+-":
                    k += 1
                while k < len(text) and text[k].isdigit():
                    k += 1
                j = k
            tokens.append(("num", float(text[i:j])))
            i = j
            continue
        if char.isalpha() or char == ".":
            j = i + 1
            while j < len(text) and (text[j].isalnum() or text[j] in "._"):
                j += 1
            tokens.append(("name", text[i:j]))
            i = j
            continue
        raise ValueError(f"cannot parse '{text}'")
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple]):
        self.tokens = tokens
        self.index = 0

    def peek(self):
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def eat(self):
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end of model expression")
        self.index += 1
        return token

    def expression(self):
        node = self.term()
        while self.peek() is not None and self.peek()[0] in {"+", "-"}:
            op = self.eat()[0]
            right = self.term()
            node = ("bin", op, node, right)
        return node

    def term(self):
        node = self.unary()
        while self.peek() is not None and self.peek()[0] in {"*", "/"}:
            op = self.eat()[0]
            right = self.unary()
            node = ("bin", op, node, right)
        return node

    def unary(self):
        if self.peek() is not None and self.peek()[0] == "-":
            self.eat()
            return ("neg", self.unary())
        if self.peek() is not None and self.peek()[0] == "+":
            self.eat()
            return self.unary()
        return self.power()

    def power(self):
        node = self.primary()
        if self.peek() is not None and self.peek()[0] == "^":
            self.eat()
            return ("bin", "^", node, self.unary())
        return node

    def primary(self):
        token = self.eat()
        kind, value = token
        if kind == "num":
            return ("num", value)
        if kind == "name":
            if self.peek() is not None and self.peek()[0] == "(":
                self.eat()
                args = []
                if self.peek() is None or self.peek()[0] != ")":
                    args.append(self.expression())
                    while self.peek() is not None and self.peek()[0] == ",":
                        self.eat()
                        args.append(self.expression())
                if self.peek() is None or self.peek()[0] != ")":
                    raise ValueError(f"missing ')' after '{value}'")
                self.eat()
                return ("call", value, tuple(args))
            return ("name", value)
        if kind == "(":
            node = self.expression()
            if self.peek() is None or self.peek()[0] != ")":
                raise ValueError("missing ')' in model expression")
            self.eat()
            return node
        raise ValueError(f"cannot parse model expression near '{value}'")
