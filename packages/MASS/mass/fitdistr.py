"""Maximum-likelihood fitting of univariate distributions (MASS fitdistr)."""

from __future__ import annotations

import inspect
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from mass.errors import MassError

_RELTEST = 10.0
_STEPREDN = 0.2
_ACCTOL = 0.0001
_SQRT_EPS = math.sqrt(2.220446049250313e-16)
_DEFAULT_ABSTOL = 1.4901161193847656e-08


class Fitdistr:
    """Return value of fitdistr, with the same fields as R's fitdistr class."""

    __slots__ = ("estimate", "sd", "vcov", "loglik", "n", "_names")

    def __init__(
        self,
        estimate: np.ndarray,
        sd: np.ndarray,
        vcov: np.ndarray,
        loglik: float,
        n: int,
        names: Sequence[str],
    ) -> None:
        self.estimate = np.asarray(estimate, dtype=float).reshape(-1)
        self.sd = np.asarray(sd, dtype=float).reshape(-1)
        self.vcov = np.asarray(vcov, dtype=float)
        self.loglik = float(loglik)
        self.n = int(n)
        self._names = tuple(names)

    def coef(self) -> np.ndarray:
        return self.estimate.copy()


def fitdistr(
    x,
    densfun,
    start=None,
    **kwargs: Any,
) -> Fitdistr:
    """Maximum-likelihood fit of a univariate distribution."""
    reserved = {"upper", "lower"}
    dots = [key for key in kwargs if key not in reserved]

    values = np.asarray(x, dtype=float).reshape(-1)
    if values.size == 0:
        raise MassError("'x' must be a non-empty numeric vector")
    if not np.all(np.isfinite(values)):
        raise MassError("'x' contains missing or infinite values")

    n = int(values.size)
    control: dict[str, Any] = {}

    if start is None:
        start_list = None
    elif isinstance(start, Mapping):
        start_list = dict(start)
    elif isinstance(start, (list, tuple)) and all(
        isinstance(item, (list, tuple)) and len(item) == 2 for item in start
    ):
        start_list = dict(start)
    else:
        start_list = dict(start)

    if densfun is None or not (
        callable(densfun) or isinstance(densfun, str)
    ):
        raise MassError("'densfun' must be supplied as a function or name")

    if isinstance(densfun, str):
        distname = densfun.lower()
        density = _named_density(distname)
        if density is None:
            raise MassError("unsupported distribution")

        if distname in ("lognormal", "log-normal"):
            if start_list is not None:
                raise MassError(
                    "supplying pars for the log-Normal distribution is not supported"
                )
            if np.any(values <= 0):
                raise MassError("need positive values to fit a log-Normal")
            return _fit_lognormal(values, n)

        if distname == "normal":
            if start_list is not None:
                raise MassError(
                    "supplying pars for the Normal distribution is not supported"
                )
            return _fit_normal(values, n)

        if distname == "poisson":
            if start_list is not None:
                raise MassError(
                    "supplying pars for the Poisson distribution is not supported"
                )
            return _fit_poisson(values, n)

        if distname == "exponential":
            if np.any(values < 0):
                raise MassError("Exponential values must be >= 0")
            if start_list is not None:
                raise MassError(
                    "supplying pars for the exponential distribution is not supported"
                )
            return _fit_exponential(values, n)

        if distname == "geometric":
            if start_list is not None:
                raise MassError(
                    "supplying pars for the geometric distribution is not supported"
                )
            return _fit_geometric(values, n)

        if distname == "weibull" and start_list is None:
            if np.any(values <= 0):
                raise MassError("Weibull values must be > 0")
            lx = np.log(values)
            m = float(np.mean(lx))
            v = float(np.var(lx, ddof=1))
            shape = 1.2 / math.sqrt(v)
            scale = math.exp(m + 0.572 / shape)
            start_list = {"shape": shape, "scale": scale}
            start_list = {
                key: val
                for key, val in start_list.items()
                if key not in dots
            }

        if distname == "gamma" and start_list is None:
            if np.any(values < 0):
                raise MassError("gamma values must be >= 0")
            m = float(np.mean(values))
            v = float(np.var(values, ddof=1))
            start_list = {"shape": m * m / v, "rate": m / v}
            start_list = {
                key: val
                for key, val in start_list.items()
                if key not in dots
            }
            control = {"parscale": [1.0, start_list["rate"]]}

        if distname == "negative binomial" and start_list is None:
            m = float(np.mean(values))
            v = float(np.var(values, ddof=1))
            size = m * m / (v - m) if v > m else 100.0
            start_list = {"size": size, "mu": m}
            start_list = {
                key: val
                for key, val in start_list.items()
                if key not in dots
            }

        if distname in ("cauchy", "logistic") and start_list is None:
            start_list = {
                "location": float(np.median(values)),
                "scale": float(np.subtract(*np.quantile(values, [0.75, 0.25]))) / 2.0,
            }
            start_list = {
                key: val
                for key, val in start_list.items()
                if key not in dots
            }

        if distname == "t" and start_list is None:
            start_list = {
                "m": float(np.median(values)),
                "s": float(np.subtract(*np.quantile(values, [0.75, 0.25]))) / 2.0,
                "df": 10.0,
            }
            start_list = {
                key: val
                for key, val in start_list.items()
                if key not in dots
            }

        dens_callable = density
    else:
        distname = None
        dens_callable = densfun

    if start_list is None or not isinstance(start_list, dict):
        raise MassError("'start' must be a named list")

    return _fit_optim(
        values,
        n,
        dens_callable,
        start_list,
        control=control,
        optim_kwargs=kwargs,
        distname=distname,
    )


def _sample_sd(values: np.ndarray) -> float:
    return float(np.sqrt(np.var(values, ddof=1)))


def _fit_normal(values: np.ndarray, n: int) -> Fitdistr:
    sd0 = _sample_sd(values) * math.sqrt((n - 1) / n)
    mx = float(np.mean(values))
    estimate = np.array([mx, sd0])
    sds = np.array([sd0 / math.sqrt(n), sd0 / math.sqrt(2 * n)])
    names = ("mean", "sd")
    vc = np.array([[sds[0] ** 2, 0.0], [0.0, sds[1] ** 2]])
    loglik = float(np.sum(_dnorm(values, mx, sd0, log=True)))
    return Fitdistr(estimate, sds, vc, loglik, n, names)


def _fit_lognormal(values: np.ndarray, n: int) -> Fitdistr:
    lx = np.log(values)
    sd0 = _sample_sd(lx) * math.sqrt((n - 1) / n)
    mx = float(np.mean(lx))
    estimate = np.array([mx, sd0])
    sds = np.array([sd0 / math.sqrt(n), sd0 / math.sqrt(2 * n)])
    names = ("meanlog", "sdlog")
    vc = np.array([[sds[0] ** 2, 0.0], [0.0, sds[1] ** 2]])
    loglik = float(np.sum(_dlnorm(values, mx, sd0, log=True)))
    return Fitdistr(estimate, sds, vc, loglik, n, names)


def _fit_poisson(values: np.ndarray, n: int) -> Fitdistr:
    estimate_val = float(np.mean(values))
    sds = np.array([math.sqrt(estimate_val / n)])
    names = ("lambda",)
    vc = np.array([[sds[0] ** 2]])
    loglik = float(np.sum(_dpois(values, estimate_val, log=True)))
    return Fitdistr(np.array([estimate_val]), sds, vc, loglik, n, names)


def _fit_exponential(values: np.ndarray, n: int) -> Fitdistr:
    estimate_val = 1.0 / float(np.mean(values))
    sds = np.array([estimate_val / math.sqrt(n)])
    names = ("rate",)
    vc = np.array([[sds[0] ** 2]])
    loglik = float(np.sum(_dexp(values, estimate_val, log=True)))
    return Fitdistr(np.array([estimate_val]), sds, vc, loglik, n, names)


def _fit_geometric(values: np.ndarray, n: int) -> Fitdistr:
    estimate_val = 1.0 / (1.0 + float(np.mean(values)))
    sds = np.array([estimate_val * math.sqrt((1.0 - estimate_val) / n)])
    names = ("prob",)
    vc = np.array([[sds[0] ** 2]])
    loglik = float(np.sum(_dgeom(values, estimate_val, log=True)))
    return Fitdistr(np.array([estimate_val]), sds, vc, loglik, n, names)


def _fit_optim(
    values: np.ndarray,
    n: int,
    densfun: Callable[..., np.ndarray | float],
    start: dict[str, float],
    *,
    control: dict[str, Any],
    optim_kwargs: dict[str, Any],
    distname: str | None,
) -> Fitdistr:
    names = list(start.keys())
    sig = inspect.signature(densfun)
    arg_names = list(sig.parameters)
    if not arg_names:
        raise MassError("'start' specifies names which are not arguments to 'densfun'")
    param_names = [name for name in arg_names if name not in {arg_names[0], "log"}]
    for name in names:
        if name not in param_names:
            raise MassError(
                "'start' specifies names which are not arguments to 'densfun'"
            )
    fixed = {
        key: optim_kwargs[key]
        for key in optim_kwargs
        if key in param_names and key not in start
    }
    optim_opts = {
        key: optim_kwargs[key]
        for key in optim_kwargs
        if key not in param_names and key not in {"upper", "lower"}
    }
    lower = optim_kwargs.get("lower")
    upper = optim_kwargs.get("upper")
    has_log = "log" in sig.parameters

    def log_density(parm: list[float]) -> np.ndarray:
        bound = {**fixed}
        for index, name in enumerate(names):
            bound[name] = parm[index]
        if has_log:
            bound["log"] = True
            out = densfun(values, **bound)
        else:
            out = densfun(values, **bound)
            out = np.log(np.asarray(out, dtype=float))
        return np.asarray(out, dtype=float)

    def objective(parm: list[float]) -> float:
        return -float(np.sum(log_density(parm)))

    par0 = [float(start[name]) for name in names]
    method = optim_opts.pop("method", None)
    if method is None:
        if lower is not None or upper is not None:
            method = "L-BFGS-B"
        elif len(names) > 1:
            method = "BFGS"
        else:
            method = "Nelder-Mead"

    parscale = control.get("parscale")
    if parscale is None:
        parscale = [1.0] * len(names)
    else:
        parscale = [float(v) for v in parscale]

    res = _optim(
        objective,
        par0,
        method=str(method),
        lower=lower,
        upper=upper,
        control=control,
        hessian=True,
        parscale=parscale,
        **optim_opts,
    )
    if res["convergence"] > 0:
        raise MassError("optimization failed")

    estimate = np.asarray(res["par"], dtype=float)
    vc = np.linalg.inv(res["hessian"])
    sds = np.sqrt(np.diag(vc))
    return Fitdistr(estimate, sds, vc, -res["value"], n, tuple(names))


def _optim(
    fn: Callable[[list[float]], float],
    par: list[float],
    *,
    method: str,
    lower=None,
    upper=None,
    control: dict[str, Any],
    hessian: bool,
    parscale: list[float],
    **_,
) -> dict[str, Any]:
    maxit = int(control.get("maxit", 500))
    reltol = float(control.get("reltol", _SQRT_EPS))
    abstol = float(control.get("abstol", _DEFAULT_ABSTOL))
    ndeps = control.get("ndeps")
    n = len(par)
    if ndeps is None:
        ndeps = [0.001] * n
    else:
        ndeps = [float(v) for v in ndeps]

    if method == "BFGS":
        scaled = [par[i] / parscale[i] for i in range(n)]

        def scaled_fn(dpar: list[float]) -> float:
            return fn([dpar[i] * parscale[i] for i in range(n)])

        def scaled_gr(dpar: list[float], gout: list[float]) -> None:
            real = [dpar[i] * parscale[i] for i in range(n)]
            for i in range(n):
                eps = ndeps[i] * (abs(real[i]) + parscale[i])
                pp = real[:]
                pm = real[:]
                pp[i] += eps
                pm[i] -= eps
                gout[i] = (fn(pp) - fn(pm)) / (2.0 * eps) * parscale[i]

        mask = [True] * n
        value, fail = _vmmin(
            n,
            scaled,
            scaled_fn,
            scaled_gr,
            maxit,
            False,
            mask,
            abstol,
            reltol,
        )
        final_par = [scaled[i] * parscale[i] for i in range(n)]
    elif method == "Nelder-Mead":
        nm = _nelder_mead(par, fn, maxit=maxit, reltol=reltol, abstol=abstol)
        final_par = nm["par"]
        value = nm["value"]
        fail = nm["convergence"]
    elif method in ("L-BFGS-B", "L-BFGS-B"):
        final_par, value, fail = _lbfgsb(
            par, fn, lower=lower, upper=upper, maxit=maxit, parscale=parscale, ndeps=ndeps
        )
    else:
        raise MassError(f"unsupported optim method {method!r}")

    hess = None
    if hessian:
        hess = _optim_hessian(fn, final_par, parscale=parscale, ndeps=ndeps)
    return {
        "par": final_par,
        "value": value,
        "convergence": fail,
        "hessian": hess,
    }


def _optim_hessian(
    fn: Callable[[list[float]], float],
    par: list[float],
    *,
    parscale: list[float],
    ndeps: list[float],
) -> np.ndarray:
    n = len(par)

    def numeric_grad(point: list[float]) -> list[float]:
        g = [0.0] * n
        for i in range(n):
            eps = ndeps[i] * (abs(point[i]) + parscale[i])
            pp = point[:]
            pm = point[:]
            pp[i] += eps
            pm[i] -= eps
            g[i] = (fn(pp) - fn(pm)) / (2.0 * eps)
        return g

    hess = np.zeros((n, n), dtype=float)
    for i in range(n):
        eps = ndeps[i] * (abs(par[i]) + parscale[i])
        pp = par[:]
        pm = par[:]
        pp[i] += eps
        pm[i] -= eps
        gp = numeric_grad(pp)
        gm = numeric_grad(pm)
        for j in range(i, n):
            hess[i, j] = (gp[j] - gm[j]) / (2.0 * eps)
            if j != i:
                hess[j, i] = hess[i, j]
    return hess


def _vmmin(n0, b, fminfn, fmingr, maxit, trace, mask, abstol, reltol, n_report=10):
    """R stats vmmin (from nnet's port of optim.c)."""
    if maxit <= 0:
        return fminfn(b), 0
    if n_report <= 0:
        raise ValueError('REPORT must be > 0 (method = "BFGS")')
    free = [i for i in range(n0) if mask[i]]
    n = len(free)
    g = [0.0] * n0
    inverse = [[0.0] * (i + 1) for i in range(n)]
    value = fminfn(b)
    if not math.isfinite(value):
        raise ValueError("initial value in 'vmmin' is not finite")
    if trace:
        sys.stdout.write("initial  value %f \n" % value)
    fmin = value
    gradcount = 1
    fmingr(b, g)
    iteration = 1
    ilast = gradcount
    count = 0
    while True:
        if ilast == gradcount:
            for i in range(n):
                row = inverse[i]
                for j in range(i):
                    row[j] = 0.0
                row[i] = 1.0
        point = [0.0] * n
        change = [0.0] * n
        step = [0.0] * n
        for i in range(n):
            point[i] = b[free[i]]
            change[i] = g[free[i]]
        gradproj = 0.0
        for i in range(n):
            total = 0.0
            row = inverse[i]
            for j in range(i + 1):
                total -= row[j] * g[free[j]]
            for j in range(i + 1, n):
                total -= inverse[j][i] * g[free[j]]
            step[i] = total
            gradproj += total * g[free[i]]
        if gradproj < 0.0:
            steplength = 1.0
            accepted = False
            while True:
                count = 0
                for i in range(n):
                    b[free[i]] = point[i] + steplength * step[i]
                    if (_RELTEST + point[i]) == (_RELTEST + b[free[i]]):
                        count += 1
                if count < n:
                    value = fminfn(b)
                    accepted = math.isfinite(value) and (
                        value <= fmin + gradproj * steplength * _ACCTOL
                    )
                    if not accepted:
                        steplength *= _STEPREDN
                if count == n or accepted:
                    break
            enough = (value > abstol) and abs(value - fmin) > reltol * (
                abs(fmin) + reltol
            )
            if not enough:
                count = n
                fmin = value
            if count < n:
                fmin = value
                fmingr(b, g)
                gradcount += 1
                iteration += 1
                curvature = 0.0
                for i in range(n):
                    step[i] = steplength * step[i]
                    change[i] = g[free[i]] - change[i]
                    curvature += step[i] * change[i]
                if curvature > 0.0:
                    quad = 0.0
                    for i in range(n):
                        total = 0.0
                        row = inverse[i]
                        for j in range(i + 1):
                            total += row[j] * change[j]
                        for j in range(i + 1, n):
                            total += inverse[j][i] * change[j]
                        point[i] = total
                        quad += total * change[i]
                    quad = 1.0 + quad / curvature
                    for i in range(n):
                        row = inverse[i]
                        for j in range(i + 1):
                            row[j] += (
                                quad * step[i] * step[j]
                                - point[i] * step[j]
                                - step[i] * point[j]
                            ) / curvature
                else:
                    ilast = gradcount
            elif ilast < gradcount:
                count = 0
                ilast = gradcount
        else:
            count = 0
            if ilast == gradcount:
                count = n
            else:
                ilast = gradcount
        if trace and iteration % n_report == 0:
            sys.stdout.write("iter%4d value %f\n" % (iteration, value))
        if iteration >= maxit:
            break
        if gradcount - ilast > 2 * n:
            ilast = gradcount
        if count == n and ilast == gradcount:
            break
    if trace:
        sys.stdout.write("final  value %f \n" % fmin)
        if iteration < maxit:
            sys.stdout.write("converged\n")
        else:
            sys.stdout.write("stopped after %i iterations\n" % iteration)
    fail = 0 if iteration < maxit else 1
    return fmin, fail


def _nelder_mead(start, fn, maxit=500, abstol=float("-inf"), reltol=None, alpha=1.0, beta=0.5, gamma=2.0):
    if reltol is None:
        reltol = _SQRT_EPS
    n = len(start)
    point = [float(value) for value in start]
    big = 1.0e35
    if maxit <= 0:
        return {"par": point, "value": float(fn(point)), "counts": 0, "convergence": 0}
    value = float(fn(point))
    if not math.isfinite(value):
        raise ValueError("function cannot be evaluated at initial parameters")
    columns = n + 2
    rows = n + 1
    simplex = [[0.0 for _ in range(columns)] for _ in range(rows)]
    funcount = 1
    convtol = reltol * (abs(value) + reltol)
    n1 = n + 1
    centroid_column = n + 1
    simplex[n][0] = value
    for i in range(n):
        simplex[i][0] = point[i]
    low = 1
    step = 0.0
    for i in range(n):
        candidate = 0.1 * abs(point[i])
        if candidate > step:
            step = candidate
    if step == 0.0:
        step = 0.1
    size = 0.0
    for j in range(2, n1 + 1):
        for i in range(n):
            simplex[i][j - 1] = point[i]
        trystep = step
        while simplex[j - 2][j - 1] == point[j - 2]:
            simplex[j - 2][j - 1] = point[j - 2] + trystep
            trystep *= 10
        size += trystep
    oldsize = size
    calcvert = True
    fail = 0
    while True:
        if calcvert:
            for j in range(n1):
                if j + 1 != low:
                    for i in range(n):
                        point[i] = simplex[i][j]
                    try:
                        value = float(fn(point))
                    except Exception:
                        value = big
                    if not math.isfinite(value):
                        value = big
                    funcount += 1
                    simplex[n][j] = value
            calcvert = False
        low_value = simplex[n][low - 1]
        high_value = low_value
        high = low
        for j in range(1, n1 + 1):
            if j != low:
                value = simplex[n][j - 1]
                if value < low_value:
                    low = j
                    low_value = value
                if value > high_value:
                    high = j
                    high_value = value
        if high_value <= low_value + convtol or low_value <= abstol:
            break
        for i in range(n):
            total = -simplex[i][high - 1]
            for j in range(n1):
                total += simplex[i][j]
            simplex[i][centroid_column] = total / n
        for i in range(n):
            point[i] = (1.0 + alpha) * simplex[i][centroid_column] - alpha * simplex[i][high - 1]
        try:
            value = float(fn(point))
        except Exception:
            value = big
        if not math.isfinite(value):
            value = big
        funcount += 1
        reflected = value
        if reflected < low_value:
            simplex[n][centroid_column] = value
            for i in range(n):
                expanded = gamma * point[i] + (1 - gamma) * simplex[i][centroid_column]
                simplex[i][centroid_column] = point[i]
                point[i] = expanded
            try:
                value = float(fn(point))
            except Exception:
                value = big
            if not math.isfinite(value):
                value = big
            funcount += 1
            if value < reflected:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = value
            else:
                for i in range(n):
                    simplex[i][high - 1] = simplex[i][centroid_column]
                simplex[n][high - 1] = reflected
        elif reflected < high_value:
            for i in range(n):
                simplex[i][high - 1] = point[i]
            simplex[n][high - 1] = reflected
        else:
            if reflected < high_value:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = reflected
            for i in range(n):
                point[i] = (1 - beta) * simplex[i][high - 1] + beta * simplex[i][centroid_column]
            try:
                value = float(fn(point))
            except Exception:
                value = big
            if not math.isfinite(value):
                value = big
            funcount += 1
            if value < simplex[n][high - 1]:
                for i in range(n):
                    simplex[i][high - 1] = point[i]
                simplex[n][high - 1] = value
            elif reflected >= high_value:
                calcvert = True
                size = 0.0
                for j in range(n1):
                    if j + 1 != low:
                        for i in range(n):
                            simplex[i][j] = beta * (simplex[i][j] - simplex[i][low - 1]) + simplex[i][low - 1]
                            size += abs(simplex[i][j] - simplex[i][low - 1])
                if size < oldsize:
                    oldsize = size
                else:
                    fail = 10
                    break
        if funcount > maxit:
            break
    result = [simplex[i][low - 1] for i in range(n)]
    if funcount > maxit:
        fail = 1
    return {
        "par": result,
        "value": simplex[n][low - 1],
        "counts": funcount,
        "convergence": fail,
    }


def _lbfgsb(par, fn, lower, upper, maxit, parscale, ndeps):
    """Minimal L-BFGS-B: box constraints via projection after each BFGS step."""
    n = len(par)
    lo = [-math.inf] * n if lower is None else list(np.broadcast_to(lower, n))
    hi = [math.inf] * n if upper is None else list(np.broadcast_to(upper, n))

    def clamp(point: list[float]) -> list[float]:
        return [min(hi[i], max(lo[i], point[i])) for i in range(n)]

    def bounded_fn(dpar: list[float]) -> float:
        return fn(clamp([dpar[i] * parscale[i] for i in range(n)]))

    scaled = [par[i] / parscale[i] for i in range(n)]

    def scaled_gr(dpar: list[float], gout: list[float]) -> None:
        real = clamp([dpar[i] * parscale[i] for i in range(n)])
        for i in range(n):
            eps = ndeps[i] * (abs(real[i]) + parscale[i])
            pp = real[:]
            pm = real[:]
            pp[i] += eps
            pm[i] -= eps
            gout[i] = (fn(pp) - fn(pm)) / (2.0 * eps) * parscale[i]

    b = scaled[:]
    mask = [True] * n
    value, fail = _vmmin(
        n,
        b,
        bounded_fn,
        scaled_gr,
        maxit,
        False,
        mask,
        _DEFAULT_ABSTOL,
        _SQRT_EPS,
    )
    final = clamp([b[i] * parscale[i] for i in range(n)])
    return final, value, fail


def _named_density(distname: str) -> Callable[..., np.ndarray] | None:
    table = {
        "beta": _dbeta,
        "cauchy": _dcauchy,
        "chi-squared": _dchisq,
        "exponential": _dexp,
        "f": _df,
        "gamma": _dgamma,
        "geometric": _dgeom,
        "log-normal": _dlnorm,
        "lognormal": _dlnorm,
        "logistic": _dlogis,
        "negative binomial": _dnbinom,
        "normal": _dnorm,
        "poisson": _dpois,
        "t": _dmyt,
        "weibull": _dweibull,
    }
    return table.get(distname)


def _dnorm(x, mean=0.0, sd=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if sd <= 0:
        out = np.full_like(x, np.nan, dtype=float)
    else:
        z = (x - mean) / sd
        logp = -0.5 * (z * z + math.log(2 * math.pi)) - math.log(sd)
        out = logp if log else np.exp(logp)
    return out


def _dlnorm(x, meanlog=0.0, sdlog=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if np.any(x <= 0):
        out = np.full_like(x, np.nan, dtype=float)
    else:
        lx = np.log(x)
        out = _dnorm(lx, meanlog, sdlog, log=log)
        if log:
            out = out - np.log(x)
        else:
            out = out / x
    return out


def _dexp(x, rate=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if rate <= 0:
        out = np.full_like(x, np.nan, dtype=float)
    else:
        logp = np.where(x >= 0, math.log(rate) - rate * x, -math.inf)
        out = logp if log else np.exp(logp)
    return out


def _dpois(x, lambda_, log=False):
    x = np.asarray(x, dtype=float)
    k = np.floor(x)
    if np.any(x != k) or np.any(x < 0):
        out = np.full_like(x, np.nan, dtype=float)
    else:
        out = _vector_dpois(k, lambda_, log=log)
    return out


def _vector_dpois(k, lambda_, log=False):
    k = np.asarray(k, dtype=float)
    if lambda_ < 0:
        return np.full_like(k, np.nan, dtype=float)
    logp = k * math.log(lambda_) - lambda_ - _lgamma(k + 1.0)
    return logp if log else np.exp(logp)


def _dgeom(x, prob, log=False):
    x = np.asarray(x, dtype=float)
    k = np.floor(x)
    if prob <= 0 or prob > 1 or np.any(x != k) or np.any(x < 0):
        out = np.full_like(x, np.nan, dtype=float)
    else:
        logp = np.where(x > 0, x * math.log1p(-prob) + math.log(prob), math.log(prob))
        out = logp if log else np.exp(logp)
    return out


def _dgamma(x, shape, rate=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if shape <= 0 or rate <= 0:
        out = np.full_like(x, np.nan, dtype=float)
    else:
        logp = (shape - 1) * np.log(x) - rate * x - shape * math.log(1.0 / rate) - _lgamma(shape)
        logp = np.where(x >= 0, logp, -math.inf)
        out = logp if log else np.exp(logp)
    return out


def _dbeta(x, shape1, shape2, log=False):
    x = np.asarray(x, dtype=float)
    if shape1 <= 0 or shape2 <= 0:
        return np.full_like(x, np.nan, dtype=float)
    logp = (
        (shape1 - 1) * np.log(x)
        + (shape2 - 1) * np.log1p(-x)
        + _lgamma(shape1 + shape2)
        - _lgamma(shape1)
        - _lgamma(shape2)
    )
    logp = np.where((x >= 0) & (x <= 1), logp, -math.inf)
    return logp if log else np.exp(logp)


def _dcauchy(x, location=0.0, scale=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if scale <= 0:
        return np.full_like(x, np.nan, dtype=float)
    z = (x - location) / scale
    logp = -math.log(math.pi) - math.log(scale) - np.log1p(z * z)
    return logp if log else np.exp(logp)


def _dchisq(x, df, log=False):
    return _dgamma(x, df / 2.0, rate=0.5, log=log)


def _df(x, df1, df2, log=False):
    x = np.asarray(x, dtype=float)
    if df1 <= 0 or df2 <= 0:
        return np.full_like(x, np.nan, dtype=float)
    logp = (
        0.5 * (df1 * math.log(df1) + df2 * math.log(df2))
        + _lgamma(0.5 * (df1 + df2))
        - _lgamma(0.5 * df1)
        - _lgamma(0.5 * df2)
        + (0.5 * df1 - 1) * np.log(x)
        - 0.5 * (df1 + df2) * np.log1p(df1 * x / df2)
    )
    logp = np.where(x >= 0, logp, -math.inf)
    return logp if log else np.exp(logp)


def _dlogis(x, location=0.0, scale=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if scale <= 0:
        return np.full_like(x, np.nan, dtype=float)
    z = (x - location) / scale
    logp = -z - 2 * np.log1p(np.exp(-z)) - math.log(scale)
    return logp if log else np.exp(logp)


def _dnbinom(x, size, mu=None, prob=None, log=False):
    x = np.asarray(x, dtype=float)
    k = np.floor(x)
    if mu is not None:
        if size <= 0 or mu < 0:
            return np.full_like(x, np.nan, dtype=float)
        prob = size / (size + mu)
    if prob is None or size <= 0 or prob <= 0 or prob > 1:
        return np.full_like(x, np.nan, dtype=float)
    if np.any(x != k) or np.any(x < 0):
        return np.full_like(x, np.nan, dtype=float)
    logp = (
        _lgamma(x + size)
        - _lgamma(size)
        - _lgamma(x + 1.0)
        + size * math.log(prob)
        + x * math.log1p(-prob)
    )
    return logp if log else np.exp(logp)


def _dmyt(x, m, s, df, log=False):
    x = np.asarray(x, dtype=float)
    if s <= 0 or df <= 0:
        return np.full_like(x, np.nan, dtype=float)
    return _dt((x - m) / s, df, log=log) - math.log(s)


def _dt(x, df, log=False):
    x = np.asarray(x, dtype=float)
    if df <= 0:
        return np.full_like(x, np.nan, dtype=float)
    logp = (
        _lgamma(0.5 * (df + 1.0))
        - _lgamma(0.5 * df)
        - 0.5 * math.log(df * math.pi)
        - 0.5 * (df + 1.0) * np.log1p(x * x / df)
    )
    return logp if log else np.exp(logp)


def _dweibull(x, shape, scale=1.0, log=False):
    x = np.asarray(x, dtype=float)
    if shape <= 0 or scale <= 0:
        return np.full_like(x, np.nan, dtype=float)
    z = x / scale
    logp = np.where(
        x >= 0,
        math.log(shape) - math.log(scale) + (shape - 1) * np.log(z) - z**shape,
        -math.inf,
    )
    return logp if log else np.exp(logp)


def _lgamma(x):
    if isinstance(x, np.ndarray):
        return np.vectorize(math.lgamma, otypes=[float])(x)
    return math.lgamma(x)
