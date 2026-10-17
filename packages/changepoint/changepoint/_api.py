"""Changepoint detection. Numeric series follow coredata of a plain vector."""

from __future__ import annotations

import ast
import math
import warnings
from datetime import datetime

import numpy as np

from changepoint import _core as C

VERSION = "2.3"
NA = np.nan


class ChangepointError(C.ChangepointError):
    pass


class Search:
    """The list PELT and BINSEG return. Index 1 is the changepoint vector, as R's [[2]]."""

    def __init__(self, cpts, cps=None, lastchangelike=None, ncpts=None, like_q=None, pen=None):
        self.cpts = np.atleast_1d(np.asarray(cpts, dtype=int))
        self.cps = cps
        self.lastchangelike = lastchangelike
        self.ncpts = ncpts
        self.like_q = like_q
        self.pen = pen

    def __getitem__(self, index):
        if index == 1:
            return self.cpts
        raise IndexError(index)


class Cpt:
    def __init__(self, kind="cpt"):
        self.kind = kind
        self.data_values = np.asarray([], dtype=float)
        self.index = np.asarray([], dtype=float)
        self.cpttype = "Not Set"
        self.method = ""
        self.test_stat = ""
        self.pen_type = ""
        self.pen_value = np.asarray([0.0])
        self.minseglen = 1
        self._cpts = np.asarray([], dtype=int)
        self.ncpts_max = np.inf
        self.param_est = {}
        now = datetime.now()
        self.date = now.strftime("%a %b ") + f"{now.day:2d}" + now.strftime(" %H:%M:%S %Y")
        self.version = VERSION
        self.cpts_full = None
        self.pen_value_full = None
        self.shape = None

    @property
    def cpts_internal(self):
        return self._cpts


def _second(out):
    if isinstance(out, Search):
        return np.atleast_1d(out.cpts)
    values = np.atleast_1d(np.asarray(out))
    return np.atleast_1d(values[1])


def _as_series(data):
    values = np.asarray(data, dtype=float)
    if values.ndim == 0:
        values = values.reshape(1)
    return values


def check_data(data):
    values = np.asarray(data)
    if not np.issubdtype(values.dtype, np.number) and values.dtype != float:
        try:
            values = values.astype(float)
        except (TypeError, ValueError) as exc:
            raise ChangepointError("Only numeric data allowed") from exc
    if np.isnan(np.asarray(values, dtype=float)).any():
        raise ChangepointError(
            "Missing value: NA is not allowed in the data as changepoint methods are only sensible for regularly spaced data."
        )


def _core(data):
    return np.asarray(data, dtype=float).reshape(-1)


def _is_matrix(data) -> bool:
    return np.asarray(data).ndim == 2


def _n_obs(data) -> int:
    values = np.asarray(data)
    if values.ndim <= 1:
        return int(values.shape[0])
    return int(values.shape[1])


def sumstat(data, mu=None):
    values = _core(data)
    if mu is None:
        mu = float(np.mean(values))
    return np.column_stack(
        [
            np.concatenate([[0.0], np.cumsum(values)]),
            np.concatenate([[0.0], np.cumsum(values**2)]),
            np.cumsum(np.concatenate([[0.0], (values - mu) ** 2])),
        ]
    )


def _manual_penalty(expression, n, diffparam):
    tree = ast.parse(str(expression), mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Call,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ChangepointError("Your manual penalty cannot be evaluated")
        if isinstance(node, ast.Name) and node.id not in {"n", "diffparam", "pi"}:
            raise ChangepointError("Your manual penalty cannot be evaluated")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id == "log"):
            raise ChangepointError("Your manual penalty cannot be evaluated")
    return float(eval(compile(tree, "<penalty>", "eval"), {"__builtins__": {}}, {"n": n, "diffparam": diffparam, "pi": math.pi, "log": math.log}))


def penalty_decision(penalty, pen_value, n, diffparam, asymcheck, method):
    pen_return = None
    if penalty in ("SIC0", "BIC0"):
        pen_return = diffparam * math.log(n)
    elif penalty in ("SIC", "BIC"):
        pen_return = (diffparam + 1) * math.log(n)
    elif penalty == "MBIC":
        pen_return = (diffparam + 2) * math.log(n)
    elif penalty in ("SIC1", "BIC1"):
        raise ChangepointError("SIC1 and BIC1 have been depreciated, use SIC or BIC for the same result.")
    elif penalty == "AIC0":
        pen_return = 2 * diffparam
    elif penalty == "AIC":
        pen_return = 2 * (diffparam + 1)
    elif penalty == "AIC1":
        raise ChangepointError("AIC1 has been depreciated, use AIC for the same result.")
    elif penalty == "Hannan-Quinn0":
        pen_return = 2 * diffparam * math.log(math.log(n))
    elif penalty == "Hannan-Quinn":
        pen_return = 2 * (diffparam + 1) * math.log(math.log(n))
    elif penalty == "Hannan-Quinn1":
        raise ChangepointError("Hannan-Quinn1 has been depreciated, use Hannan-Quinn for the same result.")
    elif penalty == "None":
        pen_return = 0
    elif penalty not in ("Manual", "Asymptotic"):
        raise ChangepointError("Unknown Penalty")
    if penalty == "Manual" and not isinstance(pen_value, (int, float, np.floating, np.integer)):
        pen_return = _manual_penalty(pen_value, n, diffparam)
    if penalty == "Manual" and isinstance(pen_value, (int, float, np.floating, np.integer)):
        pen_return = float(pen_value)
    if penalty == "Asymptotic":
        if pen_value <= 0 or pen_value > 1:
            raise ChangepointError("Asymptotic penalty values must be > 0 and <= 1")
        if method != "AMOC":
            warnings.warn(
                "Asymptotic penalty value is not accurate for multiple changes, it should be treated the same as a manual penalty choice.",
                stacklevel=2,
            )
        alpha = float(pen_value)
        if asymcheck == "mean.norm":
            alogn = (2 * math.log(math.log(n))) ** (-0.5)
            blogn = (1 / alogn) + 0.5 * alogn * math.log(math.log(math.log(n)))
            inner = (1 - alpha + math.exp(-2 * (math.pi**0.5) * math.exp(blogn / alogn))) ** (-1 / (2 * (math.pi**0.5)))
            pen_return = (-alogn * math.log(math.log(inner)) + blogn) ** 2
        elif asymcheck == "var.norm":
            alogn = math.sqrt(2 * math.log(math.log(n)))
            blogn = 2 * math.log(math.log(n)) + (math.log(math.log(math.log(n)))) / 2 - math.log(math.gamma(0.5))
            pen_return = (-(math.log(math.log((1 - alpha + math.exp(-2 * math.exp(blogn))) ** (-0.5)))) / alogn + blogn / alogn) ** 2
        elif asymcheck == "meanvar.norm":
            alogn = math.sqrt(2 * math.log(math.log(n)))
            blogn = 2 * math.log(math.log(n)) + math.log(math.log(math.log(n)))
            pen_return = (-(math.log(math.log((1 - alpha + math.exp(-2 * math.exp(blogn))) ** (-0.5)))) / alogn + blogn / alogn) ** 2
        elif asymcheck == "reg.norm":
            top = -(
                math.log(
                    math.log(
                        (
                            1
                            - alpha
                            + math.exp(
                                -2
                                * math.exp(
                                    2 * math.log(math.log(n))
                                    + (diffparam / 2) * math.log(math.log(math.log(n)))
                                    - math.log(math.gamma(diffparam / 2))
                                )
                            )
                        )
                        ** (-0.5)
                    )
                )
                + 2 * math.log(math.log(n))
                + (diffparam / 2) * math.log(math.log(math.log(n)))
                - math.log(math.gamma(diffparam / 2))
            )
            bottom = (2 * math.log(math.log(n))) ** 0.5
            pen_return = (top / bottom) ** 2
        elif asymcheck == "var.css":
            table = {0.01: 1.628, 0.05: 1.358, 0.1: 1.224, 0.25: 1.019, 0.5: 0.828, 0.75: 0.677, 0.9: 0.571, 0.95: 0.520}
            if alpha not in table:
                raise ChangepointError("Only alpha values of 0.01,0.05,0.1,0.25,0.5,0.75,0.9,0.95 are valid for CSS")
            pen_return = table[alpha]
        elif asymcheck == "mean.cusum":
            raise ChangepointError("Asymptotic penalties have not been implemented yet for CUSUM")
        elif asymcheck == "meanvar.gamma":
            raise ChangepointError("Asymptotic penalties for the Gamma test statistic are not defined, please choose an alternative penalty type")
        elif asymcheck == "meanvar.exp":
            an = (2 * math.log(math.log(n))) ** 0.5
            bn = 2 * math.log(math.log(n)) + 0.5 * math.log(math.log(math.log(n))) - 0.5 * math.log(math.pi)
            if alpha == 1:
                pen_return = 1.42417
            else:
                pen_return = (-1 / an) * math.log(-0.5 * math.log(1 - alpha)) + bn
        elif asymcheck == "meanvar.poisson":
            raise ChangepointError("Asymptotic penalties for the Poisson test statistic are not available yet, please choose an alternative penalty type")
        else:
            raise ChangepointError("Unknown Penalty")
    if pen_return < 0:
        raise ChangepointError("pen.value cannot be negative, please change your penalty value")
    return float(pen_return)


def decision(tau, null, alt=None, penalty="MBIC", n=0, diffparam=1, pen_value=0):
    tau = np.atleast_1d(np.asarray(tau, dtype=float))
    null = np.atleast_1d(np.asarray(null, dtype=float))
    if alt is None or (np.ndim(alt) == 0 and (alt is NA or (isinstance(alt, float) and math.isnan(alt)))):
        alt_values = np.full(tau.shape, NA)
    else:
        alt_values = np.atleast_1d(np.asarray(alt, dtype=float))
    if np.all(np.isnan(alt_values)):
        if len(tau) != len(null):
            raise ChangepointError("Lengths of tau and null do not match")
    elif len(tau) != len(null) or len(tau) != len(alt_values):
        raise ChangepointError("Lengths of tau, null and alt do not match")

    def one(tau_i, null_i, alt_i):
        if not np.isfinite(alt_i):
            stat = null_i
        else:
            stat = null_i - alt_i
        if stat >= pen_value:
            return tau_i
        return n

    if len(tau) == 1:
        return {"cpt": one(tau[0], null[0], alt_values[0]), "pen": pen_value}
    return {"cpt": np.asarray([one(tau[i], null[i], alt_values[i]) for i in range(len(tau))]), "pen": pen_value}


def PELT(sumstat, pen=0, cost_func="norm.mean", shape=1, minseglen=1):
    out = C.pelt(sumstat, pen, cost_func, shape, minseglen)
    return Search(cpts=out["cpts"], lastchangelike=out["lastchangelike"], ncpts=out["ncpts"])


def BINSEG(sumstat, pen=0, cost_func="norm.mean", shape=1, minseglen=2, Q=5):
    out = C.binseg(sumstat, pen, cost_func, shape, minseglen, Q)
    if out["op_cpts"] == Q and pen != 0:
        warnings.warn(
            "The number of changepoints identified is Q, it is advised to increase Q to make sure changepoints have not been missed.",
            stacklevel=2,
        )
    return Search(cpts=out["cpts"], cps=out["cps"], pen=out["pen"])


def data_input(data, method, pen_value, costfunc, minseglen, Q, var=0, shape=1):
    values = _core(data)
    mu = float(var) if var != 0 else float(np.mean(values))
    stat = sumstat(values, mu)
    if method == "PELT":
        return PELT(stat, pen=pen_value, cost_func=costfunc, minseglen=minseglen, shape=shape)
    if method == "BinSeg":
        return BINSEG(stat, pen=pen_value, cost_func=costfunc, minseglen=minseglen, Q=Q, shape=shape)
    if method == "SegNeigh":
        return SEGNEIGH(values, pen_value, costfunc, Q, var=var, shape=shape)
    raise ChangepointError("Multiple Method is not recognised")


def _set_cpts(obj: Cpt, value):
    value = np.atleast_1d(np.asarray(value, dtype=int)).reshape(-1)
    n = len(obj.data_values) if obj.kind != "cpt.reg" else obj.data_values.shape[0]
    if len(value) and value[-1] == n:
        obj._cpts = value
    else:
        obj._cpts = np.concatenate([value, [n]]) if len(value) else np.asarray([n], dtype=int)


def class_input(data, cpttype, method, test_stat, penalty, pen_value, minseglen, param_estimates, out=None, Q=NA, shape=NA):
    if method in ("BinSeg", "SegNeigh") or penalty == "CROPS":
        ans = Cpt("cpt.range")
    elif cpttype == "regression":
        ans = Cpt("cpt.reg")
    else:
        ans = Cpt("cpt")
    values = np.asarray(data, dtype=float)
    if ans.kind == "cpt.reg":
        ans.data_values = values
        ans.index = np.arange(1, values.shape[0] + 1, dtype=float)
    else:
        flat = values.reshape(-1)
        ans.data_values = flat
        ans.index = np.arange(1, len(flat) + 1, dtype=float)
    ans.cpttype = cpttype
    ans.method = method
    ans.test_stat = test_stat
    ans.pen_type = penalty
    ans.pen_value = np.atleast_1d(np.asarray(pen_value, dtype=float))
    ans.minseglen = minseglen
    if penalty != "CROPS" and out is not None:
        _set_cpts(ans, _second(out))
        if param_estimates:
            ans.shape = shape
            if ans.kind == "cpt.range" and test_stat == "Gamma":
                # param() is called before cpts.full is filled, and the shape argument lands in ncpts.
                raise ChangepointError("subscript out of bounds")
            param(ans, shape=shape)
    if method == "PELT":
        ans.ncpts_max = np.inf
    elif method == "AMOC":
        ans.ncpts_max = 1
    else:
        ans.ncpts_max = Q
    if method == "BinSeg" and isinstance(out, Search) and out.cps is not None:
        locations = out.cps[0]
        rows = [locations[: i + 1] for i in range(len(locations))]
        width = max(len(row) for row in rows)
        full = np.full((len(rows), width), NA)
        for i, row in enumerate(rows):
            full[i, : len(row)] = row
        ans.cpts_full = full
        ans.pen_value_full = out.cps[1]
    elif method == "SegNeigh" and isinstance(out, Search):
        ans.cpts_full = out.cps[1:]
        ans.pen_value_full = -np.diff(out.like_q)
    return ans


def cpts(obj: Cpt, ncpts=None):
    if ncpts is None or (isinstance(ncpts, float) and math.isnan(ncpts)):
        if len(obj._cpts) == 0:
            return np.asarray([], dtype=int)
        return obj._cpts[:-1]
    counts = np.nansum(obj.cpts_full > 0, axis=1)
    rows = np.flatnonzero(counts == ncpts)
    if len(rows) == 0:
        raise ChangepointError(
            "Your input object doesn't have a segmentation with the requested number of changepoints.\n Possible ncpts are: "
            + ",".join(str(int(v)) for v in counts)
        )
    return obj.cpts_full[rows[0], :ncpts]


def cpts_full(obj: Cpt):
    return obj.cpts_full


def data_set(obj: Cpt):
    return obj.data_values


def data_set_ts(obj: Cpt):
    return obj.data_values


def cpttype(obj: Cpt):
    return obj.cpttype


def method(obj: Cpt):
    return obj.method


def distribution(obj: Cpt):
    return obj.test_stat


def test_stat(obj: Cpt):
    return obj.test_stat


def pen_type(obj: Cpt):
    return obj.pen_type


def pen_value(obj: Cpt):
    value = obj.pen_value
    return float(value[0]) if np.size(value) == 1 else value


def pen_value_full(obj: Cpt):
    return obj.pen_value_full


def minseglen(obj: Cpt):
    return obj.minseglen


def ncpts_max(obj: Cpt):
    return obj.ncpts_max


def param_est(obj: Cpt):
    return obj.param_est


def coef(obj: Cpt):
    return obj.param_est


def ncpts(obj: Cpt):
    return int(len(cpts(obj)))


def seg_len(obj: Cpt, ncpts=None):
    if obj.kind == "cpt.range" and ncpts is not None and not (isinstance(ncpts, float) and math.isnan(ncpts)):
        points = np.concatenate([[0], np.atleast_1d(cpts(obj, ncpts)), [len(obj.data_values)]])
    else:
        points = obj._cpts
    if len(points) == 0:
        return np.asarray([], dtype=int)
    previous = np.concatenate([[0], points[:-1]])
    return points - previous


def nseg(obj: Cpt, count=None):
    if count is None or (isinstance(count, float) and math.isnan(count)):
        return ncpts(obj) + 1
    return int(count) + 1


def cpts_ts(obj: Cpt):
    points = cpts(obj)
    if len(points) == 0:
        return np.asarray([], dtype=float)
    return obj.index[points - 1]


def fit_mean(obj: Cpt, points=None):
    if points is None:
        points = np.concatenate([[0], obj._cpts])
    data = data_set(obj)
    means = []
    for left, right in zip(points[:-1], points[1:]):
        means.append(float(np.mean(data[int(left) : int(right)])))
    return np.asarray(means, dtype=float)


def fit_var(obj: Cpt, points=None):
    if points is None:
        points = np.concatenate([[0], obj._cpts])
    data = data_set(obj)
    lengths = np.diff(points)
    variances = []
    for left, right, length in zip(points[:-1], points[1:], lengths):
        piece = data[int(left) : int(right)]
        variances.append(float(np.var(piece, ddof=1) * (length - 1) / length))
    return np.asarray(variances, dtype=float)


def fit_scale(obj: Cpt, shape, points=None):
    if points is None:
        points = np.concatenate([[0], obj._cpts])
    data = data_set(obj)
    total = np.concatenate([[0.0], np.cumsum(data)])
    scales = []
    for left, right in zip(points[:-1], points[1:]):
        scales.append((total[int(right)] - total[int(left)]) / ((right - left) * shape))
    return np.asarray(scales, dtype=float)


def param(obj: Cpt, shape=None, ncpts=None):
    if shape is None:
        shape = obj.shape
    kind = obj.cpttype
    if kind == "mean":
        obj.param_est = {"mean": fit_mean(obj)}
    elif kind == "variance":
        obj.param_est = {"variance": fit_var(obj)}
    elif kind == "mean and variance":
        if obj.test_stat == "Normal":
            obj.param_est = {"mean": fit_mean(obj), "variance": fit_var(obj)}
        elif obj.test_stat == "Gamma":
            obj.param_est = {"scale": fit_scale(obj, shape), "shape": shape}
        elif obj.test_stat == "Exponential":
            obj.param_est = {"rate": 1 / fit_mean(obj)}
        elif obj.test_stat == "Poisson":
            obj.param_est = {"lambda": fit_mean(obj)}
        else:
            raise ChangepointError("Unknown test statistic for a change in mean and variance")
    elif kind == "regression":
        obj.param_est = fit_reg(obj)
    else:
        raise ChangepointError("Unknown changepoint type, must be 'mean', 'variance', 'mean and variance', 'trend', 'meanar' or 'trendar'.")
    return obj


def fit_reg(obj: Cpt):
    data = obj.data_values
    points = np.concatenate([[0], obj._cpts])
    width = data.shape[1] - 1
    beta = np.full((len(points) - 1, width), NA)
    sigma = np.full(len(points) - 1, NA)
    for j, (left, right) in enumerate(zip(points[:-1], points[1:])):
        piece = data[int(left) : int(right)]
        y = piece[:, 0]
        x = piece[:, 1:]
        coefs, _resid, _rank, _sv = np.linalg.lstsq(x, y, rcond=None)
        beta[j] = coefs
        fitted = x @ coefs
        sigma[j] = np.sum((y - fitted) ** 2) / (len(y) - len(coefs))
    return {"beta": beta, "sig2": sigma}


def fitted(obj: Cpt, ncpts=None):
    if len(obj.param_est) == 0:
        print("Calculating parameter estimates...", end="")
        param(obj)
        print("done.")
    if obj.cpttype == "variance":
        return np.repeat(obj.param_est["mean"], len(obj.data_values))
    if obj.cpttype in ("mean", "mean and variance"):
        if obj.test_stat in ("Normal", "CUSUM"):
            means = obj.param_est["mean"]
        elif obj.test_stat == "Gamma":
            means = obj.param_est["scale"] * obj.param_est["shape"]
        elif obj.test_stat == "Eobjectponential":
            means = 1 / obj.param_est["rate"]
        elif obj.test_stat == "Poisson":
            means = obj.param_est["lambda"]
        else:
            raise ChangepointError("Invalid Changepoint test statistic")
        return np.repeat(means, seg_len(obj))
    if obj.kind == "cpt.reg":
        data = obj.data_values
        points = np.concatenate([[0], obj._cpts])
        out = np.empty(data.shape[0])
        beta = obj.param_est["beta"]
        for j, (left, right) in enumerate(zip(points[:-1], points[1:])):
            out[int(left) : int(right)] = data[int(left) : int(right), 1:] @ beta[j]
        return out
    raise ChangepointError("Invalid Changepoint Type for fitted.\n Can only return fitted values for mean, variance, mean and variance")


def residuals(obj: Cpt, ncpts=None):
    if obj.kind == "cpt.reg":
        return obj.data_values[:, 0] - fitted(obj)
    return data_set(obj) - fitted(obj)


def logLik(obj: Cpt, ncpts=None):
    if len(obj.param_est) == 0:
        print("Calculating parameter estimates...", end="")
        param(obj)
        print("done.")
    n = len(obj.data_values) if obj.kind != "cpt.reg" else obj.data_values.shape[0]
    if obj.test_stat == "Normal" and obj.cpttype == "mean":
        means = np.repeat(obj.param_est["mean"], seg_len(obj))
        rss = float(np.sum((data_set(obj) - means) ** 2))
        like = n * (math.log(2 * math.pi) + math.log(rss / n) + 1)
        points = np.concatenate([[0], obj._cpts])
        lengths = np.diff(points)
        if obj.pen_type == "MBIC":
            extra = like + (nseg(obj) - 2) * float(pen_value(obj)) + float(np.sum(np.log(lengths)))
        else:
            extra = like + (nseg(obj) - 1) * float(pen_value(obj))
        return np.asarray([like, extra])
    if obj.test_stat == "Normal" and obj.cpttype == "variance":
        center = obj.param_est["mean"]
        rss = np.concatenate([[0.0], np.cumsum((data_set(obj) - center) ** 2)])
        points = np.concatenate([[0], obj._cpts])
        lengths = seg_len(obj)
        sigmas = (rss[points[1:]] - rss[points[:-1]]) / lengths
        like = n * math.log(2 * math.pi) + float(np.sum(lengths * np.log(sigmas))) + n
        if obj.pen_type == "MBIC":
            extra = like + (nseg(obj) - 2) * float(pen_value(obj)) + float(np.sum(np.log(lengths)))
        else:
            extra = like + (nseg(obj) - 1) * float(pen_value(obj))
        return np.asarray([like, extra])
    if obj.test_stat == "Normal" and obj.cpttype == "mean and variance":
        means = np.repeat(obj.param_est["mean"], seg_len(obj))
        lengths = seg_len(obj)
        sigmas = obj.param_est["variance"]
        like = n * math.log(2 * math.pi) + float(np.sum(lengths * np.log(sigmas))) + n
        if obj.pen_type == "MBIC":
            extra = like + (nseg(obj) - 2) * float(pen_value(obj)) + float(np.sum(np.log(lengths)))
        else:
            extra = like + (nseg(obj) - 1) * float(pen_value(obj))
        return np.asarray([like, extra])
    if obj.cpttype == "regression":
        return np.asarray(logLik_reg(obj))
    raise ChangepointError("Invalid Changepoint test statistic")


def logLik_reg(obj: Cpt):
    data = obj.data_values
    points = np.concatenate([[0], obj._cpts])
    total = 0.0
    for left, right, sig2 in zip(points[:-1], points[1:], obj.param_est["sig2"]):
        piece = data[int(left) : int(right)]
        resid = piece[:, 0] - piece[:, 1:] @ obj.param_est["beta"][len(total) if False else 0]
        # beta row aligned below
    likes = []
    for j, (left, right) in enumerate(zip(points[:-1], points[1:])):
        piece = data[int(left) : int(right)]
        resid = piece[:, 0] - piece[:, 1:] @ obj.param_est["beta"][j]
        nn = len(resid)
        rss = float(np.sum(resid**2))
        likes.append(nn + nn * math.log(2 * math.pi * rss) - nn * math.log(nn) if rss else 0.0)
    like = float(np.sum(likes))
    extra = like + (nseg(obj) - 1) * float(pen_value(obj))
    return np.asarray([like, extra])


def likelihood(obj: Cpt):
    return logLik(obj)


def _fmt_num(value):
    if isinstance(value, (float, np.floating)) and math.isinf(value):
        return "Inf"
    if isinstance(value, (int, np.integer)) or (isinstance(value, (float, np.floating)) and float(value).is_integer() and abs(value) < 1e15):
        return str(int(value))
    return format(float(value), ".7g")


def summary(obj: Cpt):
    print(f"Created Using changepoint version {obj.version} ")
    gap = "     " if obj.kind == "cpt.reg" else "      "
    print(f"Changepoint type{gap}: Change in {obj.cpttype} ")
    print(f"Method of analysis    : {obj.method} ")
    stat_gap = " :" if obj.kind == "cpt.reg" else "  :"
    print(f"Test Statistic{stat_gap} {obj.test_stat} ")
    pen_gap = "      :" if obj.kind == "cpt.reg" else "       :"
    print(f"Type of penalty{pen_gap} {obj.pen_type} with value, {_fmt_num(pen_value(obj))} ")
    if obj.kind != "cpt.reg":
        print(f"Minimum Segment Length : {int(obj.minseglen)} ")
    print(f"Maximum no. of cpts   : {_fmt_num(obj.ncpts_max)} ")
    points = cpts(obj)
    if len(points) <= 20:
        shown = " ".join(str(int(v)) for v in points)
        print(f"Changepoint Locations : {shown} ")
    else:
        print(f"Number of changepoints: {ncpts(obj)} ")


def show(obj: Cpt):
    if obj.kind == "cpt.reg":
        label, title = "cpt.reg", "Changepoint Regression Object"
    else:
        label, title = "cpt", "Changepoint Object"
    names = [
        "cpttype",
        "date",
        "version",
        "data.set",
        "method",
        "test.stat",
        "pen.type",
        "pen.value",
        "minseglen",
        "cpts",
        "ncpts.max",
        "param.est",
    ]
    if obj.kind == "cpt.range":
        names.extend(["cpts.full", "pen.value.full"])
    print(f"Class '{label}' : {title}")
    print(f"       ~~   : S4 class containing {len(names)} slots with names")
    print("              " + " ".join(names) + " ")
    print()
    print(f"Created on  : {obj.date}")
    print()
    print("summary(.)  :")
    print("----------")
    summary(obj)


def plot(x: Cpt, cpt_col="red", cpt_width=1, cpt_style=1, ncpts=None, diagnostic=False, **kwargs):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if diagnostic:
        counts = np.nansum(x.cpts_full > 0, axis=1)
        counts = np.concatenate([counts, [counts[-1]]])
        penalties = np.asarray(x.pen_value_full, dtype=float)
        _fig, ax = plt.subplots()
        ax.step(counts[: len(penalties)], penalties, where="post")
        ax.set_xlabel("Number of Changepoints")
        ax.set_ylabel("Penalty Value")
        return None
    if len(x.param_est) == 0:
        print("Calculating parameter estimates...", end="")
        param(x)
        print("done.")
    series = data_set(x) if x.kind != "cpt.reg" else x.data_values[:, 0]
    time = x.index
    _fig, ax = plt.subplots()
    ax.plot(time, series, color="black")
    if x.cpttype == "variance":
        for point in cpts(x):
            ax.axvline(x.index[int(point) - 1], color=cpt_col, linewidth=cpt_width)
    elif x.cpttype in ("mean", "mean and variance"):
        ax.step(time, fitted(x), where="post", color=cpt_col, linewidth=cpt_width)
    elif x.kind == "cpt.reg":
        ax.step(time, fitted(x), where="post", color=cpt_col, linewidth=cpt_width)
    else:
        raise ChangepointError("Invalid Changepoint Type for plotting.\n Can only plot mean, variance, mean and variance")
    return cpts(x)


def _single_mean_calc(data, minseglen):
    values = _core(data)
    n = len(values)
    y = np.concatenate([[0.0], np.cumsum(values)])
    y2 = np.concatenate([[0.0], np.cumsum(values**2)])
    null = y2[n] - y[n] ** 2 / n
    taustar = np.arange(minseglen, n - minseglen + 2)
    tmp = (
        y2[taustar]
        - y[taustar] ** 2 / taustar
        + (y2[n] - y2[taustar])
        - ((y[n] - y[taustar]) ** 2) / (n - taustar)
    )
    which = int(np.nanargmin(tmp))
    return np.asarray([taustar[which], null, tmp[which]], dtype=float)


def _single_var_calc(data, mu, minseglen):
    values = _core(data)
    n = len(values)
    y = np.concatenate([[0.0], np.cumsum((values - mu) ** 2)])
    null = n * math.log(y[n] / n)
    taustar = np.arange(minseglen, n - minseglen + 2)
    sigma1 = y[taustar] / taustar
    sigma1 = np.where(sigma1 <= 0, 1e-10, sigma1)
    sigman = (y[n] - y[taustar]) / (n - taustar)
    sigman = np.where(sigman <= 0, 1e-10, sigman)
    tmp = taustar * np.log(sigma1) + (n - taustar) * np.log(sigman)
    which = int(np.nanargmin(tmp))
    return np.asarray([taustar[which], null, tmp[which]], dtype=float)


def _single_meanvar_calc(data, minseglen):
    values = _core(data)
    n = len(values)
    y = np.concatenate([[0.0], np.cumsum(values)])
    y2 = np.concatenate([[0.0], np.cumsum(values**2)])
    null = n * math.log((y2[n] - (y[n] ** 2 / n)) / n)
    taustar = np.arange(minseglen, n - minseglen + 2)
    sigma1 = (y2[taustar] - (y[taustar] ** 2 / taustar)) / taustar
    sigma1 = np.where(sigma1 <= 0, 1e-10, sigma1)
    sigman = ((y2[n] - y2[taustar]) - ((y[n] - y[taustar]) ** 2 / (n - taustar))) / (n - taustar)
    sigman = np.where(sigman <= 0, 1e-10, sigman)
    tmp = taustar * np.log(sigma1) + (n - taustar) * np.log(sigman)
    which = int(np.nanargmin(tmp))
    return np.asarray([taustar[which], null, tmp[which]], dtype=float)


def _multiple(data, method, penalty, pen_value, Q, minseglen, diffparam, cost_base, cpttype, test_stat, class_flag, param_estimates, var=0, shape=1, positive=None, integer=False, mean_known=None):
    check_data(data)
    values = np.asarray(data, dtype=float)
    if positive == "negative":
        if np.any(values < 0):
            raise ChangepointError(f"{test_stat} test statistic requires positive data")
    if positive == "nonpositive":
        if np.any(values <= 0):
            raise ChangepointError(f"{test_stat} test statistic requires positive data")
    if integer and not np.all(np.asarray(values, dtype=int) == values):
        raise ChangepointError("Poisson test statistic requires integer data")
    if method not in ("PELT", "BinSeg", "SegNeigh"):
        raise ChangepointError("Multiple Method is not recognised")
    costfunc = cost_base
    if penalty == "MBIC":
        if method == "SegNeigh":
            raise ChangepointError("MBIC penalty not implemented for SegNeigh method, please choose an alternative penalty")
        costfunc = cost_base + ".mbic"
    n = _n_obs(values)
    if cost_base == "var.norm" and n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if n < (2 * minseglen):
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    pen = penalty_decision(penalty, pen_value, n, diffparam, asymcheck=costfunc, method=method)
    if not _is_matrix(values):
        mu = var
        if mean_known is not None and (not mean_known) and (isinstance(mu, float) and math.isnan(mu) or mu is None):
            mu = float(np.mean(values))
        stored_var = mu if cost_base == "var.norm" else 0
        out = data_input(values, method, pen, costfunc, minseglen, Q, var=stored_var, shape=shape)
        if not class_flag:
            return out[1]
        ans = class_input(values, cpttype, method, test_stat, penalty, pen, minseglen, param_estimates, out, Q, shape)
        if cost_base == "var.norm":
            ans.param_est = {**ans.param_est, "mean": mu}
        return ans
    answers = []
    for row in values:
        out = data_input(row, method, pen, costfunc, minseglen, Q, var=var, shape=shape)
        if class_flag:
            answers.append(class_input(row, cpttype, method, test_stat, penalty, pen, minseglen, param_estimates, out, Q, shape))
        else:
            answers.append(out[1])
    return answers


def _amoc_mean(data, penalty, pen_value, class_flag, param_estimates, minseglen):
    values = _core(data)
    n = len(values)
    if n < 2:
        raise ChangepointError("Data must have atleast 2 observations to fit a changepoint model.")
    if n < 2 * minseglen:
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    pen = penalty_decision(penalty, pen_value, n, 1, "mean.norm", "AMOC")
    tmp = _single_mean_calc(values, minseglen)
    if penalty == "MBIC":
        tmp[2] = tmp[2] + math.log(tmp[0]) + math.log(n - tmp[0] + 1)
    ans = decision(tmp[0], tmp[1], tmp[2], penalty, n, 1, pen)
    if not class_flag:
        alogn = (2 * math.log(math.log(n))) ** (-0.5)
        blogn = (1 / alogn) + 0.5 * alogn * math.log(math.log(math.log(n)))
        conf = math.exp(-2 * (math.pi**0.5) * math.exp(-alogn * math.sqrt(abs(tmp[1] - tmp[2])) + blogn / alogn)) - math.exp(
            -2 * (math.pi**0.5) * math.exp(blogn / alogn)
        )
        return np.asarray([ans["cpt"], conf])
    return class_input(values, "mean", "AMOC", "Normal", penalty, ans["pen"], minseglen, param_estimates, np.asarray([0, ans["cpt"]]))


def cpt_mean(data, penalty="MBIC", pen_value=0, method="PELT", Q=5, test_stat="Normal", class_flag=True, param_estimates=True, minseglen=1):
    check_data(data)
    if method == "SegNeigh" and minseglen > 1:
        raise ChangepointError("minseglen not yet implemented for SegNeigh method, use PELT instead.")
    if minseglen < 1:
        minseglen = 1
        warnings.warn("Minimum segment length for a change in mean is 1, automatically changed to be 1.", stacklevel=2)
    if test_stat not in ("Normal", "CUSUM"):
        raise ChangepointError("Invalid test statistic, must be Normal or CUSUM")
    if penalty == "CROPS":
        return _crops(data, method, pen_value, test_stat, class_flag, param_estimates, minseglen, "mean")
    if test_stat == "Normal":
        if method == "AMOC":
            return _amoc_mean(data, penalty, pen_value, class_flag, param_estimates, minseglen)
        if method in ("PELT", "BinSeg", "SegNeigh"):
            if method == "SegNeigh":
                warnings.warn("SegNeigh is computationally slow, use PELT instead", stacklevel=2)
            return _multiple(data, method, penalty, pen_value, Q, minseglen, 1, "mean.norm", "mean", "Normal", class_flag, param_estimates)
        raise ChangepointError("Invalid Method, must be AMOC, PELT, SegNeigh or BinSeg")
    warnings.warn("Traditional penalty values are not appropriate for the CUSUM test statistic", stacklevel=2)
    return _cusum(data, method, penalty, pen_value, Q, class_flag, param_estimates, minseglen)


def cpt_var(data, penalty="MBIC", pen_value=0, know_mean=False, mu=NA, method="PELT", Q=5, test_stat="Normal", class_flag=True, param_estimates=True, minseglen=2):
    check_data(data)
    if method == "SegNeigh" and minseglen > 2:
        raise ChangepointError("minseglen not yet implemented for SegNeigh method, use PELT instead.")
    if minseglen < 2:
        minseglen = 2
        warnings.warn("Minimum segment length for a change in variance is 2, automatically changed to be 2.", stacklevel=2)
    if penalty == "CROPS":
        return _crops(data, method, pen_value, test_stat, class_flag, param_estimates, minseglen, "var")
    if test_stat == "Normal":
        if method == "AMOC":
            return _amoc_var(data, penalty, pen_value, know_mean, mu, class_flag, param_estimates, minseglen)
        if method in ("PELT", "BinSeg", "SegNeigh"):
            if method == "SegNeigh":
                warnings.warn("SegNeigh is computationally slow, use PELT instead", stacklevel=2)
            return _multiple(
                data, method, penalty, pen_value, Q, minseglen, 1, "var.norm", "variance", "Normal", class_flag, param_estimates, var=mu, mean_known=know_mean
            )
        raise ChangepointError("Invalid Method, must be AMOC, PELT, SegNeigh or BinSeg")
    if test_stat != "CSS":
        raise ChangepointError("Invalid test statistic, must be Normal or CSS")
    warnings.warn("Traditional penalty values are not appropriate for the CSS test statistic", stacklevel=2)
    return _css(data, method, penalty, pen_value, Q, class_flag, param_estimates, minseglen)


def _amoc_var(data, penalty, pen_value, know_mean, mu, class_flag, param_estimates, minseglen):
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if n < 2 * minseglen:
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    pen = penalty_decision(penalty, pen_value, n, 1, "var.norm", "AMOC")
    if (not know_mean) and (isinstance(mu, float) and math.isnan(mu)):
        mu = float(np.mean(values))
    tmp = _single_var_calc(values, mu, minseglen)
    if penalty == "MBIC":
        tmp[2] = tmp[2] + math.log(tmp[0]) + math.log(n - tmp[0] + 1)
    ans = decision(tmp[0], tmp[1], tmp[2], penalty, n, 1, pen)
    if not class_flag:
        return np.asarray([ans["cpt"], tmp[2]])
    out = class_input(values, "variance", "AMOC", "Normal", penalty, ans["pen"], minseglen, param_estimates, np.asarray([0, ans["cpt"]]))
    out.param_est = {**out.param_est, "mean": mu}
    return out


def _amoc_meanvar(data, penalty, pen_value, class_flag, param_estimates, minseglen):
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if n < 2 * minseglen:
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    pen = penalty_decision(penalty, pen_value, n, 1, "meanvar.norm", "AMOC")
    tmp = _single_meanvar_calc(values, minseglen)
    if penalty == "MBIC":
        tmp[2] = tmp[2] + math.log(tmp[0]) + math.log(n - tmp[0] + 1)
    ans = decision(tmp[0], tmp[1], tmp[2], penalty, n, 2, pen)
    if not class_flag:
        return np.asarray([ans["cpt"], tmp[2]])
    return class_input(values, "mean and variance", "AMOC", "Normal", penalty, ans["pen"], minseglen, param_estimates, np.asarray([0, ans["cpt"]]))


def cpt_meanvar(data, penalty="MBIC", pen_value=0, method="PELT", Q=5, test_stat="Normal", class_flag=True, param_estimates=True, shape=1, minseglen=2):
    check_data(data)
    if method == "SegNeigh" and minseglen > 2:
        raise ChangepointError("minseglen not yet implemented for SegNeigh method, use PELT instead.")
    if minseglen < 2 and not (minseglen == 1 and test_stat in ("Poisson", "Exponential")):
        minseglen = 2
        warnings.warn("Minimum segment length for a change in mean and variance is 2, automatically changed to be 2.", stacklevel=2)
    if penalty == "CROPS":
        return _crops(data, method, pen_value, test_stat, class_flag, param_estimates, minseglen, "meanvar", shape)
    table = {
        "Normal": ("meanvar.norm", 2, None, False),
        "Gamma": ("meanvar.gamma", 1, "nonpositive", False),
        "Exponential": ("meanvar.exp", 1, "negative", False),
        "Poisson": ("meanvar.poisson", 1, "negative", True),
    }
    if test_stat not in table:
        raise ChangepointError("Invalid test statistic, must be Normal, Gamma, Exponential or Poisson")
    if method == "AMOC" and test_stat == "Normal":
        return _amoc_meanvar(data, penalty, pen_value, class_flag, param_estimates, minseglen)
    if method not in ("AMOC", "PELT", "BinSeg", "SegNeigh"):
        raise ChangepointError("Invalid Method, must be AMOC, PELT, SegNeigh or BinSeg")
    if method == "SegNeigh":
        warnings.warn("SegNeigh is computationally slow, use PELT instead", stacklevel=2)
    if method == "AMOC":
        return _amoc_meanvar_other(data, test_stat, penalty, pen_value, class_flag, param_estimates, shape, minseglen)
    cost, diffparam, positive, integer = table[test_stat]
    return _multiple(
        data, method, penalty, pen_value, Q, minseglen, diffparam, cost, "mean and variance", test_stat, class_flag, param_estimates, shape=shape, positive=positive, integer=integer
    )


def _crops(data, method, pen_value, test_stat, class_flag, param_estimates, minseglen, func, shape=1):
    if method != "PELT":
        raise ChangepointError('CROPS is a valid penalty choice only if method="PELT", please change your method or your penalty.')
    pen_value = np.asarray(pen_value, dtype=float)
    if pen_value.shape != (2,):
        raise ChangepointError("For CROPS, pen.value must be supplied as a numeric vector and must be of length 2")
    if pen_value[1] < pen_value[0]:
        pen_value = pen_value[::-1]
    values = _core(data)
    stat = sumstat(values)
    names = {"Normal": "norm", "Exponential": "exp", "Gamma": "gamma", "Poisson": "poisson"}
    if test_stat not in names:
        raise ChangepointError("Only Normal, Exponential, Gamma and Poisson are valid test statistics")
    costfunc = f"{func}.{names[test_stat]}"
    out = range_of_penalties(stat, costfunc, pen_value[0], pen_value[1], shape, minseglen)
    if not class_flag:
        return out
    kind = {"var": "variance", "meanvar": "mean and variance"}.get(func, "mean")
    ans = Cpt("cpt.range")
    ans.data_values = values
    ans.index = np.arange(1, len(values) + 1, dtype=float)
    ans.cpttype = kind
    ans.method = "PELT"
    ans.test_stat = test_stat
    ans.pen_type = "CROPS"
    ans.pen_value = pen_value
    ans.minseglen = minseglen
    ans.ncpts_max = np.inf
    widths = [len(item) for item in out["changepoints"]]
    full = np.full((len(widths), max(widths) if widths else 0), NA)
    for i, item in enumerate(out["changepoints"]):
        full[i, : len(item)] = item
    ans.cpts_full = full
    ans.pen_value_full = np.concatenate([out["cpt_out"][0], [pen_value[1]]])
    return ans


def range_of_penalties(stat, cost, min_pen, max_pen, shape, minseglen):
    n = stat.shape[0] - 1
    pen_interval = [float(min_pen), float(max_pen)]
    test_penalties = []
    number = []
    penal = []
    segmentations = []
    count = 0
    first = True
    while pen_interval:
        new_num = []
        new_pen = []
        new_cpts = []
        for beta in pen_interval:
            ans = PELT(stat, pen=beta, cost_func=cost, shape=shape, minseglen=minseglen)
            found = ans.cpts
            new_num.append(len(found))
            new_cpts.append(found[:-1])
            new_pen.append(ans.lastchangelike[n] - (ans.ncpts[n] - 1) * beta)
        if first:
            print(f"Maximum number of runs of algorithm = {new_num[0] - new_num[1] + 2}")
            first = False
        count += len(new_num)
        print(f"Completed runs = {count}")
        test_penalties = sorted(set(test_penalties + pen_interval))
        number = number + new_num
        penal = penal + new_pen
        segmentations = segmentations + new_cpts
        order = np.argsort(-np.asarray(number))
        number = [number[i] for i in order]
        penal = sorted(penal)
        segmentations = [segmentations[i] for i in np.argsort([-len(item) for item in segmentations])]
        pen_interval = []
        for i in range(len(test_penalties) - 1):
            if abs(number[i] - number[i + 1]) > 1:
                gap = (penal[i + 1] - penal[i]) / (number[i] - number[i + 1])
                pen_interval.append(gap)
        kept = []
        for beta in pen_interval:
            nearest = min(test_penalties, key=lambda item: abs(item - beta))
            if not math.isclose(beta, nearest, rel_tol=0, abs_tol=1e-8):
                kept.append(beta)
        pen_interval = kept
    for j in range(len(test_penalties) - 1, 0, -1):
        if number[j] == number[j - 1]:
            del number[j]
            del test_penalties[j]
            del penal[j]
            del segmentations[j]
    beta_int = []
    beta_e = []
    for k in range(len(test_penalties)):
        beta_int.append(test_penalties[0] if k == 0 else beta_e[k - 1])
        if k == len(test_penalties) - 1:
            beta_e.append(test_penalties[k])
        else:
            beta_e.append((penal[k] - penal[k + 1]) / (number[k + 1] - number[k]))
    cpt_out = np.vstack([beta_int, number, penal])
    return {"cpt_out": cpt_out, "changepoints": segmentations}


def segneigh_mean_norm(data, Q=5, pen=0):
    values = _core(data)
    n = len(values)
    if n < 2:
        raise ChangepointError("Data must have atleast 2 observations to fit a changepoint model.")
    if np.size(pen) > 1:
        raise ChangepointError("Penalty must be a single value and not a vector")
    if Q > (n - 2):
        raise ChangepointError(f"Q is larger than the maximum number of segments {n - 2}")
    all_seg = np.zeros((n, n))
    for i in range(n):
        ssq = 0.0
        total = 0.0
        for j in range(i, n):
            length = j - i + 1
            total += values[j]
            ssq += values[j] ** 2
            all_seg[i, j] = -0.5 * (ssq - (total**2) / length)
    like_q = np.zeros((Q, n))
    like_q[0] = all_seg[0]
    cp = np.full((Q, n), NA)
    for q in range(1, Q):
        for j in range(q, n):
            v = np.arange(q - 1, j)
            like = like_q[q - 1, v] + all_seg[v + 1, j]
            like_q[q, j] = np.max(like)
            cp[q, j] = int(np.argmax(like)) + q
    cps_q = np.full((Q, Q), NA)
    for q in range(1, Q):
        cps_q[q, 0] = cp[q, n - 1]
        for i in range(q):
            previous = cps_q[q, i]
            if not np.isfinite(previous) or previous <= 0:
                break
            cps_q[q, i + 1] = cp[q - i - 1, int(previous) - 1]
    k = np.arange(Q)
    criterion = -2 * like_q[:, n - 1] + k * pen
    op_cps = int(np.argmin(criterion))
    if op_cps == Q - 1:
        warnings.warn(
            "The number of segments identified is Q, it is advised to increase Q to make sure changepoints have not been missed.",
            stacklevel=2,
        )
    if op_cps == 0:
        found = np.asarray([n], dtype=int)
    else:
        row = cps_q[op_cps]
        found = np.asarray(sorted(int(v) for v in row if np.isfinite(v) and v > 0) + [n], dtype=int)
    ordered = np.sort(np.where(np.isnan(cps_q), np.inf, cps_q), axis=1)
    ordered = np.where(np.isinf(ordered), NA, ordered)
    return Search(cpts=found, cps=ordered, like_q=-2 * like_q[:, n - 1])


def _segneigh_wide(all_seg, Q, pen, short, like_mode):
    """Segment neighbourhood when a segment needs two observations. short is 'inf' or 'one'."""
    n = all_seg.shape[0]
    like_q = np.zeros((Q, n))
    like_q[0] = all_seg[0]
    cp = np.full((Q, n), NA)
    for q in range(1, Q):
        for j in range(q, n):
            j_r = j + 1
            q_r = q + 1
            if (j_r - 2 - q_r) < 0:
                if short == "inf":
                    like = np.asarray([-np.inf])
                else:
                    v = np.asarray([q])
                    like = like_q[q - 1, v] + all_seg[v + 1, j]
            else:
                v = np.arange(q, j - 1)
                like = like_q[q - 1, v] + all_seg[v + 1, j]
            like_q[q, j] = np.max(like)
            cp[q, j] = int(np.argmax(like)) + q + 1
    return _segneigh_collect(like_q, cp, Q, pen, like_mode)


def _segneigh_collect(like_q, cp, Q, pen, like_mode):
    n = like_q.shape[1]
    cps_q = np.full((Q, Q), NA)
    for q in range(1, Q):
        cps_q[q, 0] = cp[q, n - 1]
        for i in range(q):
            previous = cps_q[q, i]
            if not np.isfinite(previous) or previous <= 0:
                break
            cps_q[q, i + 1] = cp[q - i - 1, int(previous) - 1]
    column = like_q[:, n - 1]
    criterion = -2 * column + np.arange(Q) * pen
    op_cps = int(np.argmin(criterion))
    if op_cps == Q - 1:
        warnings.warn(
            "The number of segments identified is Q, it is advised to increase Q to make sure changepoints have not been missed.",
            stacklevel=2,
        )
    if op_cps == 0:
        found = np.asarray([n], dtype=int)
    else:
        row = cps_q[op_cps]
        found = np.asarray(sorted(int(v) for v in row if np.isfinite(v) and v > 0) + [n], dtype=int)
    ordered = np.sort(np.where(np.isnan(cps_q), np.inf, cps_q), axis=1)
    ordered = np.where(np.isinf(ordered), NA, ordered)
    stored = -2 * column if like_mode == "neg2" else column
    return Search(cpts=found, cps=ordered, like_q=stored)


def segneigh_var_norm(data, Q=5, pen=0, mu=0):
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if Q > ((n / 2) + 1):
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / 2) + 1}")
    all_seg = np.zeros((n, n))
    for i in range(n):
        ssq = 0.0
        for j in range(i, n):
            length = j - i + 1
            ssq += (values[j] - mu) ** 2
            sigmasq = 1e-11 / length if ssq <= 0 else ssq / length
            all_seg[i, j] = -(length / 2) * (math.log(2 * math.pi) + math.log(sigmasq) + 1)
    return _segneigh_wide(all_seg, Q, pen, "inf", "neg2")


def segneigh_meanvar_norm(data, Q=5, pen=0):
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if Q > ((n / 2) + 1):
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / 2) + 1}")
    all_seg = np.zeros((n, n))
    for i in range(n):
        total = 0.0
        ssq = 0.0
        for j in range(i, n):
            length = j - i + 1
            total += values[j]
            ssq += values[j] ** 2
            sigmasq = (1 / length) * (ssq - (total**2) / length)
            if sigmasq <= 0:
                sigmasq = 1e-11
            all_seg[i, j] = -(length / 2) * (math.log(2 * math.pi) + math.log(sigmasq) + 1)
    return _segneigh_wide(all_seg, Q, pen, "inf", "neg2")


def segneigh_meanvar_exp(data, Q=5, pen=0):
    values = _core(data)
    if np.any(values <= 0):
        raise ChangepointError("Exponential test statistic requires positive data")
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if Q > (n - 2):
        raise ChangepointError(f"Q is larger than the maximum number of segments {n - 2}")
    all_seg = np.zeros((n, n))
    for i in range(n):
        total = 0.0
        for j in range(i, n):
            length = j - i + 1
            total += values[j]
            all_seg[i, j] = length * math.log(length) - length * math.log(total)
    return _segneigh_wide(all_seg, Q, pen, "one", "raw")


def segneigh_meanvar_gamma(data, shape=1, Q=5, pen=0):
    values = _core(data)
    if np.any(values <= 0):
        raise ChangepointError("Gamma test statistic requires positive data")
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if Q > (n - 2):
        raise ChangepointError(f"Q is larger than the maximum number of segments {n - 2}")
    all_seg = np.zeros((n, n))
    for i in range(n):
        total = 0.0
        for j in range(i, n):
            length = j - i + 1
            total += values[j]
            all_seg[i, j] = length * shape * math.log(length * shape) - length * shape * math.log(total)
    return _segneigh_wide(all_seg, Q, pen, "one", "raw")


def segneigh_meanvar_poisson(data, Q=5, pen=0):
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if Q > ((n / 2) + 1):
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / 2) + 1}")
    all_seg = np.zeros((n, n))
    for i in range(n):
        total = 0.0
        for j in range(i, n):
            length = j - i + 1
            total += values[j]
            all_seg[i, j] = -np.inf if total == 0 else total * math.log(total) - total * math.log(length)
    return _segneigh_wide(all_seg, Q, pen, "one", "raw")


def SEGNEIGH(data, pen_value, costfunc, Q, var=0, shape=1):
    if Q <= 0:
        raise ChangepointError("Q is the maximum number of changepoints so should be greater than 0")
    parts = costfunc.split(".")
    name = ".".join(parts[:2])
    if name in ("mean.norm", "norm.mean"):
        return segneigh_mean_norm(data, Q, pen_value)
    if name == "var.norm":
        return segneigh_var_norm(data, Q, pen_value, mu=var)
    if name == "meanvar.norm":
        return segneigh_meanvar_norm(data, Q, pen_value)
    if name == "meanvar.exp":
        return segneigh_meanvar_exp(data, Q, pen_value)
    if name == "meanvar.gamma":
        # The R call is segneigh.meanvar.gamma(data, Q, pen), so shape receives Q and Q receives the penalty.
        return segneigh_meanvar_gamma(data, shape=Q, Q=int(pen_value), pen=0)
    if name == "meanvar.poisson":
        return segneigh_meanvar_poisson(data, Q, pen_value)
    raise ChangepointError(f"SegNeigh cost {costfunc} is not available")


def _candidate_binseg(n, Q, score, minseglen):
    tau = [0, n]
    locations = np.zeros(Q)
    stats = np.zeros(Q)
    oldmax = np.inf
    for q in range(Q):
        lam = np.zeros(n - 1)
        i = 1
        st = tau[0] + 1
        end = tau[1]
        for j in range(1, n):
            if j == end:
                st = end + 1
                i += 1
                end = tau[i]
            elif (j - st) >= minseglen and (end - j) >= minseglen:
                lam[j - 1] = score(st, j, end)
        k = int(np.argmax(np.abs(lam))) + 1
        height = float(np.max(np.abs(lam)))
        locations[q] = k
        stats[q] = min(oldmax, height)
        oldmax = stats[q]
        tau.append(k)
        tau.sort()
    return locations, stats


def _keep_from_stats(locations, stats, pen, n):
    keep = np.flatnonzero(stats >= pen)
    op_cps = 0 if len(keep) == 0 else int(keep[-1]) + 1
    if op_cps == len(stats):
        warnings.warn(
            "The number of changepoints identified is Q, it is advised to increase Q to make sure changepoints have not been missed.",
            stacklevel=2,
        )
    if op_cps == 0:
        found = np.asarray([n], dtype=int)
    else:
        found = np.asarray(sorted(int(v) for v in locations[:op_cps]) + [n], dtype=int)
    return Search(cpts=found, cps=np.vstack([locations, stats]))


def _cusum_binseg(data, Q, pen, minseglen):
    values = _core(data)
    n = len(values)
    if n < 2:
        raise ChangepointError("Data must have atleast 2 observations to fit a changepoint model.")
    if Q > ((n / 2) + 1):
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / 2) + 1}")
    y = np.concatenate([[0.0], np.cumsum(values)])

    def score(st, j, end):
        return ((y[j] - y[st - 1]) - ((j - st + 1) / (end - st + 1)) * (y[end] - y[st - 1])) / (end - st + 1)

    locations, stats = _candidate_binseg(n, Q, score, minseglen)
    return _keep_from_stats(locations, stats, pen, n)


def _css_binseg(data, Q, pen, minseglen):
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if Q > ((n / 2) + 1):
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / 2) + 1}")
    y2 = np.concatenate([[0.0], np.cumsum(values**2)])

    def score(st, j, end):
        return math.sqrt((end - st + 1) / 2) * ((y2[j] - y2[st - 1]) / (y2[end] - y2[st - 1]) - (j - st + 1) / (end - st + 1))

    locations, stats = _candidate_binseg(n, Q, score, minseglen)
    return _keep_from_stats(locations, stats, pen, n)


def _cusum_amoc(values, minseglen):
    n = len(values)
    centered = np.concatenate([[0.0], np.cumsum(values - np.mean(values))]) / n
    window = centered[minseglen - 1 : n - minseglen + 1]
    tau = int(np.argmax(np.abs(window))) + minseglen
    return np.asarray([tau, np.max(np.abs(window))], dtype=float)


def _chain_cps(cp, Q):
    cps_q = np.full((Q, Q), NA)
    n = cp.shape[1]
    for q in range(1, Q):
        cps_q[q, 0] = cp[q, n - 1]
        for i in range(q):
            previous = cps_q[q, i]
            if not np.isfinite(previous) or previous <= 0:
                break
            cps_q[q, i + 1] = cp[q - i - 1, int(previous) - 1]
    ordered = np.sort(np.where(np.isnan(cps_q), np.inf, cps_q), axis=1)
    return cps_q, np.where(np.isinf(ordered), NA, ordered)


def _cusum_segneigh(data, Q, pen):
    values = _core(data)
    n = len(values)
    if Q > (n - 2):
        raise ChangepointError(f"Q is larger than the maximum number of segments {n - 2}")
    y = np.concatenate([[0.0], np.cumsum(values)])
    like_q = np.zeros((Q, n))
    cp = np.full((Q, n), NA)
    for q in range(1, Q):
        q_r = q + 1
        for j in range(q, n):
            j_r = j + 1
            v = np.arange(q - 1, j)
            if q_r == 2:
                like = np.abs((y[v + 1] - ((v + 1) / j_r) * y[j_r]) / j_r)
            else:
                earlier = cp[q - 1, v]
                like = like_q[q - 1, v] + np.abs(
                    (
                        (y[v + 1] - y[earlier.astype(int)])
                        - ((v + 1 - earlier) / (j_r - earlier)) * (y[j_r] - y[earlier.astype(int)])
                    )
                    / (j_r - earlier)
                )
            like_q[q, j] = np.nanmax(like)
            cp[q, j] = int(np.nanargmax(like)) + q
    cps_q, ordered = _chain_cps(cp, Q)
    op_cps = 0
    flag = False
    for q in range(1, Q):
        row = cps_q[q, :q]
        finite = [int(v) for v in row if np.isfinite(v)]
        points = [0, *sorted(finite), n]
        for i in range(len(points) - 2):
            left, mid, right = points[i], points[i + 1], points[i + 2]
            width = right - left
            stat = abs(((y[mid] - y[left]) - ((mid - left) / width) * (y[right] - y[left])) / width)
            if stat < pen:
                flag = True
        if flag:
            break
        op_cps += 1
    if op_cps == 0:
        found = np.asarray([n], dtype=int)
    else:
        row = cps_q[op_cps]
        found = np.asarray(sorted(int(v) for v in row if np.isfinite(v) and v > 0) + [n], dtype=int)
    return Search(cpts=found, cps=ordered, like_q=like_q[:, n - 1])


def _css_segneigh(data, Q, pen):
    values = _core(data)
    n = len(values)
    if Q > ((n / 2) + 1):
        raise ChangepointError(f"Q is larger than the maximum number of segments {(n / 2) + 1}")
    y2 = np.concatenate([[0.0], np.cumsum(values**2)])
    like_q = np.zeros((Q, n))
    cp = np.full((Q, n), NA)
    for q in range(1, Q):
        q_r = q + 1
        for j in range(q, n):
            j_r = j + 1
            v = np.arange(q - 1, j)
            if q_r == 2:
                like = np.abs(np.sqrt(j_r / 2) * (y2[v + 1] / y2[j_r] - (v + 1) / j_r))
            else:
                earlier = cp[q - 1, v]
                like = like_q[q - 1, v] + np.abs(
                    np.sqrt((j_r - earlier) / 2)
                    * ((y2[v + 1] - y2[earlier.astype(int)]) / (y2[j_r] - y2[earlier.astype(int)]) - (v + 1 - earlier) / (j_r - earlier))
                )
            like_q[q, j] = np.nanmax(like)
            cp[q, j] = int(np.nanargmax(like)) + q
    cps_q, ordered = _chain_cps(cp, Q)
    op_cps = 0
    flag = False
    for q in range(1, Q):
        row = [int(v) for v in cps_q[q, :q] if np.isfinite(v)]
        points = [0, *sorted(row), n]
        for i in range(len(points) - 2):
            left, mid, right = points[i], points[i + 1], points[i + 2]
            stat = abs(
                math.sqrt((right - left) / 2)
                * ((y2[mid] - y2[left]) / (y2[right] - y2[left]) - (mid - left) / (right - left))
            )
            if stat < pen:
                flag = True
        if flag:
            break
        op_cps += 1
    if op_cps == 0:
        found = np.asarray([n], dtype=int)
    else:
        row = cps_q[op_cps]
        found = np.asarray(sorted(int(v) for v in row if np.isfinite(v) and v > 0) + [n], dtype=int)
    return Search(cpts=found, cps=ordered, like_q=like_q[:, n - 1])


def _css_amoc(values, minseglen):
    n = len(values)
    y2 = np.concatenate([[0.0], np.cumsum(values**2)])
    taustar = np.arange(minseglen, n - minseglen + 2)
    tmp = (y2[taustar] / y2[n]) - taustar / n
    return np.asarray([int(np.nanargmax(np.abs(tmp))) + 1, math.sqrt(n / 2) * np.nanmax(np.abs(tmp))], dtype=float)


def _nonparametric_object(values, cpttype, test_stat, penalty, pen, minseglen, param_estimates, cpt, n):
    ans = Cpt("cpt")
    ans.data_values = values
    ans.index = np.arange(1, n + 1, dtype=float)
    ans.cpttype = cpttype
    ans.method = "AMOC"
    ans.test_stat = test_stat
    ans.pen_type = penalty
    ans.pen_value = np.asarray([pen])
    ans.minseglen = minseglen
    ans.ncpts_max = 1
    _set_cpts(ans, np.asarray([n] if cpt == n else [cpt, n]))
    if param_estimates:
        param(ans)
    return ans


def _cusum(data, method, penalty, pen_value, Q, class_flag, param_estimates, minseglen):
    if method == "PELT":
        raise ChangepointError("CUSUM does not satisfy the assumptions of PELT, use SegNeigh or BinSeg instead.")
    if penalty == "MBIC":
        raise ChangepointError("MBIC penalty is not valid for nonparametric test statistics.")
    if method not in ("AMOC", "SegNeigh", "BinSeg"):
        raise ChangepointError("Invalid Method, must be AMOC, SegNeigh or BinSeg")
    values = _core(data)
    n = len(values)
    if n < 2:
        raise ChangepointError("Data must have atleast 2 observations to fit a changepoint model.")
    if n < 2 * minseglen:
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    pen = penalty_decision(penalty, pen_value, n, 1, "mean.cusum", method)
    if method == "AMOC":
        tmp = _cusum_amoc(values, minseglen)
        ans = decision(tmp[0], tmp[1], None, penalty, n, 1, pen)
        if not class_flag:
            return ans["cpt"]
        return _nonparametric_object(values, "mean", "CUSUM", penalty, ans["pen"], minseglen, param_estimates, ans["cpt"], n)
    out = _cusum_binseg(values, Q, pen, minseglen) if method == "BinSeg" else _cusum_segneigh(values, Q, pen)
    if not class_flag:
        return out
    return class_input(values, "mean", method, "CUSUM", penalty, pen, minseglen, param_estimates, out, Q)


def _css(data, method, penalty, pen_value, Q, class_flag, param_estimates, minseglen):
    if method == "PELT":
        raise ChangepointError("CSS does not satisfy the assumptions of PELT, use SegNeigh or BinSeg instead.")
    if penalty == "MBIC":
        raise ChangepointError("MBIC penalty is not valid for nonparametric test statistics.")
    if method not in ("AMOC", "SegNeigh", "BinSeg"):
        raise ChangepointError("Invalid Method, must be AMOC, SegNeigh or BinSeg")
    values = _core(data)
    n = len(values)
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if n < 2 * minseglen:
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    pen = penalty_decision(penalty, pen_value, n, 1, "var.css", method)
    if method == "AMOC":
        tmp = _css_amoc(values, minseglen)
        ans = decision(tmp[0], tmp[1], None, "Manual", n, 1, pen)
        if not class_flag:
            return ans["cpt"]
        return _nonparametric_object(values, "variance", "CSS", penalty, ans["pen"], minseglen, param_estimates, ans["cpt"], n)
    out = _css_binseg(values, Q, pen, minseglen) if method == "BinSeg" else _css_segneigh(values, Q, pen)
    if not class_flag:
        return out
    return class_input(values, "variance", method, "CSS", penalty, pen, minseglen, param_estimates, out, Q)


def _positive_split(values, minseglen, null, segment):
    n = len(values)
    y = np.concatenate([[0.0], np.cumsum(values)])
    taustar = np.arange(minseglen, n - minseglen + 1)
    tmp = segment(y, taustar, n)
    tmp = np.where(np.isfinite(tmp), tmp, np.inf)
    which = int(np.argmin(tmp))
    return np.asarray([taustar[which], null(y, n), tmp[which]], dtype=float)


def _amoc_meanvar_other(data, test_stat, penalty, pen_value, class_flag, param_estimates, shape, minseglen):
    values = _core(data)
    n = len(values)
    if test_stat == "Exponential" and np.any(values < 0):
        raise ChangepointError("Exponential test statistic requires positive data")
    if test_stat == "Gamma" and np.any(values <= 0):
        raise ChangepointError("Gamma test statistic requires positive data")
    if test_stat == "Poisson":
        if np.any(values < 0):
            raise ChangepointError("Poisson test statistic requires positive data")
        if not np.all(values == np.floor(values)):
            raise ChangepointError("Poisson test statistic requires integer data")
    if n < 4:
        raise ChangepointError("Data must have atleast 4 observations to fit a changepoint model.")
    if n < 2 * minseglen:
        raise ChangepointError("Minimum segment legnth is too large to include a change in this data")
    asym = {"Exponential": "meanvar.exp", "Gamma": "meanvar.gamma", "Poisson": "meanvar.poisson"}[test_stat]
    decided = penalty_decision(penalty, pen_value, n, 1, asym, "AMOC")
    pen = pen_value if test_stat == "Exponential" else decided
    if test_stat == "Exponential":
        tmp = _positive_split(
            values,
            minseglen,
            lambda y, n: 2 * n * math.log(y[n]) - 2 * n * math.log(n),
            lambda y, tau, n: 2 * tau * np.log(y[tau]) - 2 * tau * np.log(tau) + 2 * (n - tau) * np.log(y[n] - y[tau]) - 2 * (n - tau) * np.log(n - tau),
        )
    elif test_stat == "Gamma":
        tmp = _positive_split(
            values,
            minseglen,
            lambda y, n: 2 * n * shape * math.log(y[n]) - 2 * n * shape * math.log(n * shape),
            lambda y, tau, n: (
                2 * tau * shape * np.log(y[tau])
                - 2 * tau * shape * np.log(tau * shape)
                + 2 * (n - tau) * shape * np.log(y[n] - y[tau])
                - 2 * (n - tau) * shape * np.log((n - tau) * shape)
            ),
        )
    else:
        def null(y, n):
            return np.inf if y[n] == 0 else 2 * y[n] * math.log(n) - 2 * y[n] * math.log(y[n])

        def segment(y, tau, n):
            left = y[tau]
            right = y[n] - y[tau]
            return 2 * np.log(tau) * left - 2 * left * np.log(left) + 2 * np.log(n - tau) * right - 2 * right * np.log(right)

        tmp = _positive_split(values, minseglen, null, segment)
    if penalty == "MBIC":
        tmp[2] = tmp[2] + math.log(tmp[0]) + math.log(n - tmp[0] + 1)
    ans = decision(tmp[0], tmp[1], tmp[2], penalty, n, 1, pen)
    if not class_flag:
        return ans["cpt"]
    return class_input(values, "mean and variance", "AMOC", test_stat, penalty, ans["pen"], minseglen, param_estimates, np.asarray([0, ans["cpt"]]), shape=shape)


def check_reg_data(data):
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ChangepointError("Argument 'data' must be a numerical matrix.")
    n, width = values.shape
    p = width - 1
    if p == 0:
        raise ChangepointError("Dimension of data is 1, no regressors found.")
    if n < p:
        raise ChangepointError("More regressors than observations.")
    intercept = np.all(values[:, 1] == values[0, 1])
    if not intercept:
        warnings.warn("Missing intercept regressor. Appending 1's to right of data.", stacklevel=2)
        values = np.column_stack([values, np.ones(n)])
    return values


def cpt_reg(data, penalty="MBIC", pen_value=0, method="PELT", test_stat="Normal", class_flag=True, param_estimates=True, shape=0, minseglen=3, tol=1e-07):
    check_data(data)
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ChangepointError("Argument 'data' must be a numerical matrix/array.")
    if method not in ("AMOC", "PELT"):
        raise ChangepointError("Invalid method, must be AMOC or PELT.")
    if test_stat != "Normal":
        warnings.warn(f"test.stat = {test_stat} is not supported. Converted to test.stat='Normal'", stacklevel=2)
        test_stat = "Normal"
    if penalty == "CROPS":
        raise ChangepointError("CROPS has not yet been implemented for cpt.reg")
    if values.ndim == 2:
        series = values.reshape(1, *values.shape)
    else:
        series = values
    answers = []
    for item in series:
        checked = check_reg_data(item)
        pen = penalty_decision(penalty, pen_value, checked.shape[0], checked.shape[1] - 1, "reg.norm", method)
        if method == "PELT":
            found = C.reg_pelt(checked, pen, minseglen, shape, tol)
            cpt_values = found["cpts"]
        else:
            found = C.reg_amoc(checked, pen, minseglen, shape, tol)
            chosen = decision(found["cpts"][0], found["null"], found["alt"], penalty, checked.shape[0], checked.shape[1] - 1, pen)
            cpt_values = np.asarray([chosen["cpt"]])
        if not class_flag:
            answers.append(np.sort(cpt_values))
            continue
        ans = Cpt("cpt.reg")
        ans.data_values = checked
        ans.index = np.arange(1, checked.shape[0] + 1, dtype=float)
        ans.cpttype = "regression"
        ans.method = method
        ans.test_stat = test_stat
        ans.pen_type = penalty
        ans.pen_value = np.asarray([pen])
        ans.minseglen = minseglen
        _set_cpts(ans, cpt_values)
        ans.ncpts_max = np.inf if method == "PELT" else 1
        if param_estimates:
            param(ans)
        answers.append(ans)
    return answers[0] if len(answers) == 1 else answers


def data_set_set(obj: Cpt, value):
    values = np.asarray(value, dtype=float)
    if obj.kind == "cpt.reg":
        obj.data_values = values
    else:
        flat = values.reshape(-1)
        obj.data_values = flat
        obj.index = np.arange(1, len(flat) + 1, dtype=float)
    return obj


def cpttype_set(obj: Cpt, value):
    obj.cpttype = value
    return obj


def method_set(obj: Cpt, value):
    obj.method = value
    return obj


def distribution_set(obj: Cpt, value):
    obj.test_stat = value
    return obj


def test_stat_set(obj: Cpt, value):
    obj.test_stat = value
    return obj


def pen_type_set(obj: Cpt, value):
    obj.pen_type = value
    return obj


def pen_value_set(obj: Cpt, value):
    obj.pen_value = np.atleast_1d(np.asarray(value, dtype=float))
    return obj


def minseglen_set(obj: Cpt, value):
    obj.minseglen = value
    return obj


def cpts_set(obj: Cpt, value):
    _set_cpts(obj, value)
    return obj


def ncpts_max_set(obj: Cpt, value):
    obj.ncpts_max = value
    return obj


def param_est_set(obj: Cpt, value):
    obj.param_est = value
    return obj


def cpts_full_set(obj: Cpt, value):
    obj.cpts_full = np.asarray(value, dtype=float)
    return obj


def pen_value_full_set(obj: Cpt, value):
    obj.pen_value_full = np.atleast_1d(np.asarray(value, dtype=float))
    return obj


class_input.__name__ = "class_input"
