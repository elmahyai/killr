"""Nonlinear quantile regression, as nlrq.R defines it.

The model is a formula such as "y ~ a * exp(b * x)" with the data as a
dictionary of columns and the start values as a dictionary. The R closures
of nlrqModel are a class here, with the same fields and methods.
"""

from __future__ import annotations

import ast
import math

import numpy as np
import rlbfgsb
from scipy.stats import t as student_t

from quantreg.fit import rq_fit
from quantreg.infer import summary_rq
from quantreg.messages import nlrq_control

_DBL_EPS = float(np.finfo(float).eps)
# numericDeriv default eps is .Machine$double.eps^(1/2) when central = FALSE.
_NUMERIC_EPS = _DBL_EPS ** 0.5
# optim's numerical gradient uses ndeps = 1e-3 for L-BFGS-B.
_NDEPS = 1e-3

def _exp_scalar(value):
    try:
        return math.exp(value)
    except OverflowError:
        return math.inf


# numpy's exp differs from the C library exp, which R calls, by one ulp on some inputs.
# numericDeriv divides that by the step, so the gradient would differ by about 1e-8.
_LIBM_EXP = np.frompyfunc(_exp_scalar, 1, 1)


def _libm_exp(values):
    return np.asarray(_LIBM_EXP(values), dtype=float)


_FUNCTIONS = {
    "exp": _libm_exp,
    "log": np.log,
    "sqrt": np.sqrt,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "abs": np.abs,
    "pi": math.pi,
}


def _split_formula(formula):
    text = str(formula)
    if "~" not in text:
        raise ValueError("formula has no ~")
    lhs, rhs = text.split("~", 1)
    return lhs.strip(), rhs.strip()


def _compile(text):
    # R's power operator is ^. Python spells it **.
    tree = ast.parse(text.replace("^", "**"), mode="eval")
    return compile(tree, "<formula>", "eval")


def _rho(residuals, tau):
    residuals = np.asarray(residuals, dtype=float)
    return tau * np.maximum(residuals, 0.0) + (tau - 1.0) * np.minimum(residuals, 0.0)




def _lsfit(x, y, wt):
    """Weighted least squares as lsfit(x, y, wt, intercept = FALSE) returns it."""
    root = np.sqrt(wt)
    coef = np.linalg.lstsq(x * root[:, None], y * root, rcond=None)[0]
    return coef, y - x @ coef


def _qr_resid(x, y):
    """qr.resid(qr(x), y): the part of y outside the column space of x."""
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    return y - x @ coef


class NlrqModel:
    """The nlrqModel object. Fields mirror the R closures; methods are plain."""

    def __init__(self, formula, tau, data, start):
        lhs_text, rhs_text = _split_formula(formula)
        self.formula_text = str(formula)
        self._lhs_code = _compile(lhs_text)
        self._rhs_code = _compile(rhs_text)
        self._data = {key: np.asarray(value, dtype=float) for key, value in data.items()}
        self._names = list(start.keys())
        self._params = {}
        self._ind = {}
        length = 0
        for name in self._names:
            value = np.atleast_1d(np.asarray(start[name], dtype=float)).reshape(-1).copy()
            self._params[name] = value
            self._ind[name] = np.arange(length, length + value.size)
            length += value.size
        self._tau = float(tau)
        self._lhs = np.broadcast_to(self._evaluate(self._lhs_code, {}), self._n_rows()).astype(float)
        self.rho = None
        self._refresh()

    def _n_rows(self):
        lengths = [value.shape[0] for value in self._data.values() if value.ndim == 1]
        return max(lengths) if lengths else 1

    def _env(self, extra=None):
        env = dict(_FUNCTIONS)
        env.update(self._data)
        env.update(self._params)
        if extra:
            env.update(extra)
        return env

    def _evaluate(self, code, extra):
        return eval(code, {"__builtins__": {}}, self._env(extra))

    def _rhs_value(self):
        return np.broadcast_to(self._evaluate(self._rhs_code, {}), self._n_rows()).astype(float).copy()

    def _numeric_rhs(self):
        """numericDeriv(form[[3]], names(ind), env): the value and its forward-difference gradient."""
        base = self._rhs_value()
        columns = []
        for name in self._names:
            for j in range(self._params[name].size):
                original = self._params[name][j]
                magnitude = abs(original)
                delta = _NUMERIC_EPS if magnitude == 0 else magnitude * _NUMERIC_EPS
                self._params[name][j] = original + delta
                shifted = self._rhs_value()
                self._params[name][j] = original
                columns.append((shifted - base) / delta)
        gradient = np.column_stack(columns) if columns else np.zeros((base.shape[0], 0))
        return base, gradient

    def _refresh(self):
        self._rhs, self._grad = self._numeric_rhs()
        self._resid = self._lhs - self._rhs
        self._dev = float(np.sum(_rho(self._resid, self._tau)))

    def _rank_deficient(self):
        grad = self._grad
        if grad.size == 0:
            return False
        sv = np.linalg.svd(grad, compute_uv=False)
        return bool(np.sum(sv > 1e-7 * sv[0]) < min(grad.shape))

    def resid(self):
        return self._resid.copy()

    def fitted(self):
        return self._rhs.copy()

    def gradient(self):
        return self._grad.copy()

    def Rmat(self):
        """Rmat(): qr.R of the gradient at the current parameters, as the R closure returns it."""
        return np.linalg.qr(self._grad, mode="r")

    def formula(self):
        return self.formula_text

    def tau(self):
        return self._tau

    def deviance(self):
        return self._dev

    def getPars(self):
        if not self._names:
            return np.zeros(0)
        return np.concatenate([self._params[name] for name in self._names])

    def getAllPars(self):
        return self.getPars()

    def parameter_names(self):
        names = []
        for name in self._names:
            size = self._params[name].size
            names.extend([name] if size == 1 else [f"{name}{j + 1}" for j in range(size)])
        return names

    def setPars(self, new_pars):
        values = np.asarray(new_pars, dtype=float).reshape(-1)
        for name in self._names:
            self._params[name] = values[self._ind[name]].copy()
        self._refresh()
        return self._rank_deficient()

    def changeTau(self, new_tau):
        self._tau = float(new_tau)
        self._dev = float(np.sum(_rho(self._resid, self._tau)))
        return self._dev

    def incr(self):
        return np.linalg.lstsq(self._grad, self._resid, rcond=None)[0]

    def predict(self, newdata=None):
        """predict(newdata): the right-hand side on new columns, with the fitted parameters."""
        extra = {key: np.asarray(value, dtype=float) for key, value in dict(newdata or {}).items()}
        rows = max((value.shape[0] for value in extra.values() if value.ndim == 1), default=1)
        values = self._evaluate(self._rhs_code, extra)
        return np.broadcast_to(values, rows).astype(float).copy()

    def trace(self):
        print(f"{_format_number(self._dev)}: {_format_vector(self.getPars())}")


def nlrq_model(form, tau, data, start):
    """nlrqModel(form, tau, data, start): the fitting state for one formula."""
    return NlrqModel(form, tau, data, start)


def _meketon(x, y, w, tau, ctrl):
    """One weighted-L1 step. Returns the coefficient step and the updated dual weights."""
    yw = ctrl["big"]
    k = 1
    eps = ctrl["eps"]
    beta = ctrl["beta"]
    coef = None
    while k <= ctrl["k"] and yw - float(np.sum(y * w)) > eps:
        d = np.minimum(tau - w, 1 - tau + w)
        coef, resid = _lsfit(x, y, d ** 2)
        yw = float(np.sum(_rho(resid, tau)))
        k += 1
        s = resid * d ** 2
        alpha = max(eps, float(np.max(np.maximum(s / (tau - w), -s / (1 - tau + w)))))
        w = w + (beta / alpha) * s
    return coef, w


def _optim_lambda(model, step, pars, lam0, method):
    """optim(par = lam0, fn = model.step, method, lower = 0, upper = 1), as R calls it.

    The L-BFGS-B step is R's own kernel, crates/rlbfgsb, with optim's defaults:
    factr 1e7, pgtol 0, lmm 5, maxit 100, and the numerical gradient ndeps 1e-3.
    """
    if method != "L-BFGS-B":
        raise NotImplementedError("nlrq is checked with method L-BFGS-B only")

    def step_fn(lam):
        model.setPars(pars + lam[0] * step)
        return model.deviance()

    try:
        out = rlbfgsb.optim_lbfgsb(
            step_fn,
            [float(lam0)],
            [0.0],
            [1.0],
            [_NDEPS],
            factr=1e7,
            pgtol=0.0,
            lmm=5,
            maxit=100,
        )
    except Exception as exc:
        # nlrq.R wraps optim in try(), so any optim error becomes this stop().
        raise RuntimeError("optim unable to find valid step size") from exc
    return float(out["par"][0])


def _calc(model, ctrl, trace, method):
    n = model.resid().shape[0]
    tau = model.tau()
    w = np.zeros(n)
    snew = model.deviance()
    sold = ctrl["big"]
    nit = 0
    lam0 = ctrl["InitialStepSize"]
    eps = ctrl["eps"]
    if trace:
        model.trace()
    while sold - snew > eps and nit < ctrl["maxiter"]:
        coef, w_new = _meketon(model.gradient(), model.resid(), w, tau, ctrl)
        step = coef
        pars = model.getPars()
        lam = _optim_lambda(model, step, pars, lam0, method)
        if not math.isfinite(lam):
            raise RuntimeError("optim unable to find valid step size")
        if trace:
            print("lambda =", lam)
        model.setPars(pars + lam * step)
        sold = snew
        snew = model.deviance()
        w = _qr_resid(model.gradient(), w_new)
        w1 = float(np.max(np.maximum(w, 0.0)))
        if w1 > tau:
            w = (w * tau) / (w1 + eps)
        w0 = float(np.max(np.maximum(-w, 0.0)))
        if w0 > 1 - tau:
            w = (w * (1 - tau)) / (w0 + eps)
        if trace:
            model.trace()
        nit += 1
    model.rho = float(np.sum(_rho(model.resid(), tau)))
    return model


def nlrq(formula, data, start, tau=0.5, control=None, trace=False, method="L-BFGS-B", data_name="data"):
    """Nonlinear quantile regression. start must be given; getInitial is not translated."""
    ctrl = nlrq_control()
    if control:
        ctrl.update(dict(control))
    model = nlrq_model(formula, tau, data, start)
    _calc(model, ctrl, trace, method)
    call = {"formula": str(formula), "tau": tau, "trace": trace, "control": dict(ctrl)}
    return {"m": model, "data": data_name, "call": call, "class": "nlrq"}


# ---- S3 methods on the nlrq object ----

def coef_nlrq(object):
    """coef.nlrq: every parameter, in model order."""
    return object["m"].getAllPars()


def deviance_nlrq(object):
    return object["m"].deviance()


def tau_nlrq(object):
    return object["m"].tau()


def fitted_nlrq(object):
    """fitted.nlrq: fitted values as a plain vector. The R label attribute is not carried."""
    return np.asarray(object["m"].fitted(), dtype=float).reshape(-1)


def formula_nlrq(x):
    return x["m"].formula()


def residuals_nlrq(object, type="response"):
    """residuals.nlrq: the response residuals, or the quantile rho residuals."""
    if type not in ("response", "rho"):
        raise ValueError("'arg' should be one of \"response\", \"rho\"")
    value = np.asarray(object["m"].resid(), dtype=float).reshape(-1)
    if type == "rho":
        tau = object["m"].tau()
        return tau * np.maximum(value, 0.0) + (1 - tau) * np.minimum(value, 0.0)
    return value


def predict_nlrq(object, newdata=None):
    """predict.nlrq: fitted values, or the model evaluated at newdata."""
    if newdata is None:
        return fitted_nlrq(object)
    return object["m"].predict(newdata)


def logLik_nlrq(object):
    """logLik.nlrq: n * (log(tau * (1 - tau)) - 1 - log(rho / n)), with df = number of parameters."""
    model = object["m"]
    n = model.resid().shape[0]
    p = model.getPars().shape[0]
    tau = model.tau()
    fidelity = model.rho
    value = n * (math.log(tau * (1 - tau)) - 1 - math.log(fidelity / n))
    return {"value": value, "n": n, "df": p}


def AIC_nlrq(object, k=2):
    """AIC.nlrq: -2 * logLik + k * df. k <= 0 uses log(n). The edf is the df."""
    likelihood = logLik_nlrq(object)
    penalty = float(k)
    if penalty <= 0:
        penalty = math.log(likelihood["n"])
    return {"value": -2.0 * likelihood["value"] + penalty * likelihood["df"], "edf": likelihood["df"]}


def extractAIC_nlrq(fit, scale=0, k=2):
    """extractAIC.nlrq: c(edf, AIC).

    R calls AIC(fit, k) with k passed positionally, so it lands in the ... of
    AIC.nlrq and the penalty stays 2. The k argument here is ignored for the same reason.
    """
    del scale, k
    scored = AIC_nlrq(fit)
    return np.array([scored["edf"], scored["value"]], dtype=float)


# ---- printing ----

def _format_number(value):
    """format(x) with 7 significant digits, fixed notation as R uses it here."""
    text = f"{float(value):.7g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        sign = exponent[0]
        digits = exponent[1:].lstrip("0").rjust(2, "0")
        return f"{mantissa}e{sign}{digits}"
    return text


def _decimals_needed(value, digits=7):
    if value == 0 or not math.isfinite(value):
        return 0
    text = f"{abs(value):.{digits - 1}e}"
    mantissa, exponent = text.split("e")
    mantissa = mantissa.replace(".", "").rstrip("0")
    exponent = int(exponent)
    return max(0, len(mantissa) - 1 - exponent)


def _format_vector(values):
    """format() of a numeric vector: 7 significant digits, one common number of decimals."""
    values = [float(item) for item in np.asarray(values, dtype=float).reshape(-1)]
    decimals = max((_decimals_needed(item) for item in values), default=0)
    return " ".join(f"{item:.{decimals}f}" for item in values)


def print_nlrq(x):
    """print.nlrq: the model, the data name, tau, deviance, and the parameters. Returns the text."""
    model = x["m"]
    lines = [
        "Nonlinear quantile regression",
        f"   model:  {model.formula()} ",
        f"    data:  {x['data']} ",
        f"     tau:  {repr(float(model.tau()))} ",
        f"deviance:  {_format_number(model.deviance())} ",
    ]
    lines.extend(_format_named(model.getAllPars(), model.parameter_names()))
    return "\n".join(lines) + "\n"


def _format_named(values, names):
    """print() of a named numeric vector: names above their right-aligned values."""
    texts = _format_vector(values).split(" ")
    # R prints every column at one common width: the widest value or name.
    width = max([len(text) for text in texts] + [len(name) for name in names])
    head = "".join(name.rjust(width) + " " for name in names)
    body = "".join(text.rjust(width) + " " for text in texts)
    return [head, body]


# ---- summary.nlrq and print.summary.nlrq ----

def summary_nlrq(object, R=200):
    """summary.nlrq: the nlrq parameters with bootstrap standard errors.

    R fits rq(y ~ X - 1, tau) to the residuals and the gradient, takes
    summary(se = "boot", covariance = TRUE), then puts the nlrq parameters in
    the Value column and recomputes t and Pr(>|t|). The bootstrap draws come
    from R's generator through quantreg.boot, so set the seed first.
    """
    model = object["m"]
    residual = np.asarray(model.resid(), dtype=float).reshape(-1)
    gradient = np.asarray(model.gradient(), dtype=float)
    tau = float(model.tau())
    pnames = model.parameter_names()
    fit = rq_fit(gradient, residual, tau=tau, method="br")
    linear = {
        "x": gradient,
        "y": residual,
        "coefficients": np.asarray(fit["coefficients"], dtype=float),
        "residuals": np.asarray(fit["residuals"], dtype=float),
        "tau": tau,
        "names": [f"X{j + 1}" for j in range(gradient.shape[1])],
        "method": "br",
    }
    f = summary_rq(linear, se="boot", covariance=True, R=R)
    table = np.array(f["coefficients"], dtype=float)
    table[:, 0] = model.getPars()
    table[:, 2] = table[:, 0] / table[:, 1]
    rdf = f["rdf"]
    table[:, 3] = 2.0 * (1.0 - student_t.cdf(np.abs(table[:, 2]), rdf)) if rdf > 0 else np.nan
    f["coefficients"] = table
    f["names"] = pnames
    f["call"] = object.get("call")
    f["tau"] = tau
    f["class"] = "summary.nlrq"
    return f


def _format_matrix_cells(values):
    """format(round(m, digits)) on a matrix: one common number of decimals and one common width."""
    flat = [float(item) for item in np.asarray(values, dtype=float).reshape(-1)]
    decimals = max((_decimals_needed(item) for item in flat), default=0)
    texts = [f"{item:.{decimals}f}" for item in flat]
    width = max((len(text) for text in texts), default=0)
    return [text.rjust(width) for text in texts]


def _call_text(call):
    """dput of the call. The Python fit keeps the formula and tau only, not data or start."""
    if isinstance(call, dict):
        return f"nlrq(formula = {call['formula']}, tau = {_format_number(call['tau'])})"
    return "" if call is None else str(call)


def print_summary_nlrq(x, digits=5):
    """print.summary.nlrq: the call, tau, and the coefficient table rounded to digits. Returns the text."""
    table = np.round(np.asarray(x["coefficients"], dtype=float), digits)
    tau = round(float(x["tau"]), digits)
    names = list(x["names"])
    columns = list(x.get("columns") or ["Value", "Std. Error", "t value", "Pr(>|t|)"])
    cells = np.array(_format_matrix_cells(table), dtype=object).reshape(table.shape)
    row_width = max([len(name) for name in names] + [0])
    widths = [
        max([len(columns[j])] + [len(cells[i, j]) for i in range(table.shape[0])])
        for j in range(table.shape[1])
    ]
    lines = ["", f"Call: {_call_text(x.get('call'))}", "", f"tau: [1] {_format_number(tau)}", "", "Coefficients:"]
    lines.append(" " * row_width + "".join(" " + columns[j].ljust(widths[j]) for j in range(table.shape[1])))
    for i, name in enumerate(names):
        lines.append(name.ljust(row_width) + "".join(" " + cells[i, j].ljust(widths[j]) for j in range(table.shape[1])))
    return "\n".join(lines) + "\n"
