"""Steady-state solvers from rootSolve.

``stode`` follows the Fortran Newton loop in ``dSteady``: a forward
difference Jacobian, a dense or banded linear solve, and the same
stopping tests. ``stodes`` uses that dense Newton. On the linear
problems in the manual the sparse code and this Newton agree inside
1e-8. ``runsteady`` integrates with LSODA and stops when the mean
absolute derivative drops below ``stol``, which is the test in
``call_runsteady``.
"""

import math
import warnings

import numpy as np

from rootSolve._vec import Vector


class SteadyResult:
    """A steady-state list: the state, the precision trace, and attributes."""

    def __init__(self, y, precis, steady, names=None):
        self.y = Vector(y, names)
        self.precis = [float(item) for item in precis]
        self.steady = bool(steady)
        self.extra = {}
        self.nspec = None
        self.dimens = None
        self.ynames = None
        self.classes = ["rootSolve", "list"]
        self.time = None
        self.steps = None

    def __str__(self):
        lines = ["$y", " " + " ".join(f"{value:.7g}" for value in self.y)]
        for name, values in self.extra.items():
            flat = np.ravel(np.asarray(values, dtype=float))
            lines.append(f"${name}")
            lines.append(" " + " ".join(f"{value:.7g}" for value in flat))
        lines.append("precis")
        lines.append(" " + " ".join(f"{value:.7g}" for value in self.precis))
        lines.append("steady")
        lines.append(" TRUE" if self.steady else " FALSE")
        return "\n".join(lines)


class MultiRoot:
    """The list ``multiroot`` returns."""

    def __init__(self, root, f_root, iterations, estim_precis, names=None):
        self.root = Vector(root, names)
        self.f_root = Vector(f_root)
        self.iter = int(iterations)
        self.estim_precis = float(estim_precis)

    def __str__(self):
        return "\n".join([
            "$root",
            " " + " ".join(f"{value:.7g}" for value in self.root),
            "$f.root",
            " " + " ".join(f"{value:.7g}" for value in self.f_root),
            "$iter",
            f" {self.iter}",
            "$estim.precis",
            f" {self.estim_precis:.7g}",
        ])


def _numeric(values, what):
    if values is None:
        raise ValueError(f"`{what}' must be numeric")
    if isinstance(values, bool):
        raise ValueError(f"`{what}' must be numeric")
    try:
        array = np.array(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"`{what}' must be numeric") from exc
    if array.dtype.kind not in "fc" or np.iscomplexobj(array):
        raise ValueError(f"`{what}' must be numeric")
    return np.asarray(array, dtype=float)


def _state(y):
    names = None
    if isinstance(y, Vector):
        return np.asarray(y.values, dtype=float), (
            list(y.names) if y.names is not None else None
        )
    if isinstance(y, dict):
        return np.asarray(list(y.values()), dtype=float), list(y.keys())
    array = _numeric(y, "y")
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        array = np.ravel(array, order="F")
    return array, names


def _scalar_or_vector(value, n, what):
    array = np.atleast_1d(_numeric(value, what))
    if array.size == 1:
        return np.repeat(float(array.reshape(-1)[0]), 1)
    flat = np.ravel(array, order="F")
    if flat.size != n:
        if what == "atol":
            raise ValueError(
                "`atol' must either be a scalar, or as long as `start'"
            )
        raise ValueError(
            "`rtol' must either be a scalar, or as long as `y'"
        )
    return flat


def _weights(y, rtol, atol):
    n = len(y)
    r = np.atleast_1d(np.asarray(rtol, dtype=float))
    a = np.atleast_1d(np.asarray(atol, dtype=float))
    if r.size == 1 and a.size == 1:
        return r[0] * np.abs(y) + a[0]
    if r.size == 1 and a.size == n:
        return r[0] * np.abs(y) + a
    if r.size == n and a.size == 1:
        return r * np.abs(y) + a[0]
    return r * np.abs(y) + a


def _perturb_at(values, index):
    """Fortran ``Perturb``: step is at least 1e-8, and the value is moved."""
    step = abs(values[index]) * 1e-8
    if step < 1e-8:
        step = 1e-8
    values[index] = values[index] + step
    return step


def _as_rates(result, n, label):
    if not isinstance(result, (list, tuple)):
        raise ValueError("Model function must return a list\n")
    if len(result) == 0:
        raise ValueError(
            "Model function must return a list of values, of which first "
            "element has length =length of y\n "
        )
    first = result[0]
    if isinstance(first, Vector):
        rates = [float(item) for item in first.values]
    elif isinstance(first, np.ndarray):
        rates = [float(item) for item in np.ravel(first, order="F")]
    elif isinstance(first, (list, tuple)):
        rates = [float(item) for item in first]
    else:
        rates = [float(first)]
    if len(rates) != n:
        raise ValueError(
            "The number of derivatives returned by "
            + label
            + f"{len(rates)}must equal the length of the initial conditions "
            + f"vector ({n})"
        )
    if any(math.isnan(item) for item in rates):
        raise ValueError(
            "Model function must return a list of values, of which first "
            "element has length =length of y\n "
        )
    return rates, result[1:]


def _call_model(func, time, y, parms, names, kwargs):
    state = Vector(np.asarray(y, dtype=float), names)
    return func(float(time), state, parms, **kwargs)


def _positivity_spec(positive, n):
    if isinstance(positive, bool):
        return positive, []
    if positive is None:
        return False, []
    try:
        indices = [int(item) for item in positive]
    except TypeError as exc:
        raise ValueError(
            "'positive' should either be TRUE/FALSE or\n"
            "      a VECTOR with indices to the state variables that have to "
            "be positive"
        ) from exc
    if not indices:
        return False, []
    if max(indices) > n:
        raise ValueError(
            "the elements of 'positive' should be < the number of state variables"
        )
    if min(indices) < 1:
        raise ValueError("the elements of 'positive' should be >0")
    return False, indices


def _clamp(y, positivity, indices):
    if positivity:
        np.maximum(y, 0.0, out=y)
    elif len(indices) > 1:
        for index in indices:
            y[index - 1] = max(0.0, y[index - 1])


def _full_jacobian(model, y):
    n = len(y)
    rate = np.asarray(model(y), dtype=float)
    beta = -rate
    copy = np.array(y, dtype=float, copy=True)
    alpha = np.zeros((n, n))
    for column in range(n):
        step = _perturb_at(copy, column)
        shifted = np.asarray(model(copy), dtype=float)
        alpha[:, column] = (shifted + beta) / step
        copy[column] = y[column]
    return alpha, beta


def _band_jacobian(model, y, bandup, banddown):
    """Banded difference, with several columns perturbed in one model call.

    The packed matrix is the storage ``scipy.linalg.solve_banded`` solves.
    ``beta`` is still ``-f``, the way the factorisation sees it.
    """
    n = len(y)
    mu = int(bandup)
    ml = int(banddown)
    niter = min(n, ml + mu + 1)
    nband = ml + mu + 1
    old = np.array(y, dtype=float, copy=True)
    rate = np.asarray(model(y), dtype=float)
    beta = -rate
    packed = np.zeros((ml + mu + 1, n))
    work = np.array(y, dtype=float, copy=True)
    for start in range(niter):
        columns = list(range(start, n, nband))
        steps = {}
        for column in columns:
            steps[column] = _perturb_at(work, column)
        shifted = np.asarray(model(work), dtype=float)
        for column, step in steps.items():
            scale = 1.0 / step
            first = max(column - mu, 0)
            last = min(column + ml, n - 1)
            for row in range(first, last + 1):
                packed[mu + row - column, column] = (
                    shifted[row] + beta[row]
                ) * scale
        work[:] = old
    return packed, beta, mu, ml


def _solve_full(alpha, beta):
    try:
        return np.linalg.solve(alpha, beta)
    except np.linalg.LinAlgError:
        warnings.warn(
            "error during factorisation of matrix (dgefa); singular matrix",
            stacklevel=3,
        )
        print("diagonal element is zero")
        return None


def _newton(model, y, rtol, atol, ctol, maxiter, bandup, banddown, banded,
            positivity, indices):
    """One Newton loop. Returns the state, the precision trace, and a flag.

    Convergence is tested on ``-f`` before the linear solve, matching
    ``dSteady``. A step whose largest absolute entry is at most ``ctol``
    is kept, and one more model call records the next precision.
    """
    from scipy.linalg import solve_banded

    state = np.array(y, dtype=float, copy=True)
    precis = []
    reached = False
    for k in range(1, int(maxiter) + 1):
        ewt = _weights(state, rtol, atol)
        if banded:
            packed, beta, mu, ml = _band_jacobian(
                model, state, bandup, banddown,
            )
        else:
            alpha, beta = _full_jacobian(model, state)
        precis.append(float(np.mean(np.abs(beta))))
        if float(np.max(np.abs(beta / ewt))) <= 1.0:
            reached = True
            break
        if banded:
            try:
                delta = solve_banded((mu, ml), packed, beta)
            except np.linalg.LinAlgError:
                warnings.warn(
                    "error during factorisation of matrix (dgbfa); "
                    "singular matrix",
                    stacklevel=3,
                )
                print("diagonal element is zero")
                break
        else:
            delta = _solve_full(alpha, beta)
            if delta is None:
                break
        relative = float(np.max(np.abs(delta)))
        state = state + delta
        _clamp(state, positivity, indices)
        if relative <= ctol:
            reached = True
            if k < int(maxiter):
                residual = np.asarray(model(state), dtype=float)
                precis.append(float(np.mean(np.abs(residual))))
            break
    if not reached:
        warnings.warn("steady-state not reached", stacklevel=3)
    return state, precis, reached


def _prepare_times(times):
    if times is None:
        return 0.0
    array = _numeric(times, "times")
    flat = np.atleast_1d(array).reshape(-1)
    if flat.size > 1:
        warnings.warn(
            "`times' should be one number - taking first value",
            stacklevel=3,
        )
    if flat.size == 0:
        return 0.0
    return float(flat[0])


def _check_solver_args(y, func, maxiter, rtol, atol, ctol, dllname):
    if isinstance(func, str):
        if not isinstance(dllname, str):
            raise ValueError(
                "You need to specify the name of the dll or shared library "
                "where 'func' can be found (without extension)"
            )
        raise ValueError(
            "cannot calculate steady-state: dyn function not loaded: " + func
        )
    if not callable(func):
        raise ValueError(
            "`func' must be a function or character vector or a compiled function"
        )
    try:
        count = int(maxiter)
    except (TypeError, ValueError) as exc:
        raise ValueError("`maxiter' must be numeric") from exc
    if isinstance(maxiter, bool) or count < 1:
        if isinstance(maxiter, bool):
            raise ValueError("`maxiter' must be numeric")
        raise ValueError("'maxiter' must be >=1")
    _numeric(rtol, "rtol")
    _numeric(atol, "atol")
    _numeric(ctol, "ctol")
    if np.atleast_1d(_numeric(ctol, "ctol")).size > 1:
        raise ValueError("`ctol' must be a scalar")
    return count


def _model_of(func, time, parms, names, use_names, kwargs, label):
    def model(state):
        called = names if use_names else None
        result = _call_model(func, time, state, parms, called, kwargs)
        rates, _extras = _as_rates(result, len(state), label)
        return rates

    return model


def stode(y, times=0, func=None, parms=None, rtol=1e-6, atol=1e-8,
          ctol=1e-8, jactype="fullint", jacfunc=None, verbose=False,
          bandup=1, banddown=1, positive=False, maxiter=100, ynames=True,
          dllname=None, **kwargs):
    """Newton steady state. ``jactype`` selects a full or banded Jacobian."""
    if func is None:
        raise ValueError(
            "`func' must be a function or character vector or a compiled function"
        )
    state, names = _state(y)
    n = len(state)
    count = _check_solver_args(state, func, maxiter, rtol, atol, ctol, dllname)
    time = _prepare_times(times)
    kind = jactype
    if kind == "1D":
        kind = "1Dint"
    banded = kind in ("bandint", "bandusr", "1Dint")
    if kind in ("fullusr", "bandusr") and jacfunc is None:
        raise ValueError(
            "stode: cannot estimate steady-state: *jacfunc* NOT specified; "
            "either specify *jacfunc* or change *jactype*"
        )
    if kind not in ("fullint", "fullusr", "bandusr", "bandint", "1Dint"):
        raise ValueError(
            "'jactype' must be one of 'fullint', 'fullusr', 'bandusr', "
            "or 'bandint'"
        )
    if banded and (bandup is None or banddown is None):
        raise ValueError("bandup and banddown must be specified if banded jacobian")
    positivity, indices = _positivity_spec(positive, n)
    label = "'func() ("
    if kind == "fullusr":
        def model(state):
            called = names if ynames else None
            result = _call_model(func, time, state, parms, called, kwargs)
            rates, _extras = _as_rates(result, len(state), label)
            return rates

        def newton_model(state):
            return model(state)

        # A supplied Jacobian replaces the difference columns.
        base = _model_of(func, time, parms, names, ynames, kwargs, label)

        def full_user(state):
            rate = np.asarray(base(state), dtype=float)
            called = Vector(state, names if ynames else None)
            matrix = jacfunc(float(time), called, parms, **kwargs)
            alpha = np.array(matrix, dtype=float)
            if alpha.shape != (n, n):
                raise ValueError("Jacobian dimension not ok")
            return alpha, -rate

        # Run the shared loop with a one-off full Jacobian by inlining.
        solved, precis, reached = _newton_user(
            base, full_user, state, rtol, atol, float(ctol), count,
            positivity, indices,
        )
    else:
        model = _model_of(func, time, parms, names, ynames, kwargs, label)
        # Touch the model once so a bad return fails before the loop.
        model(state)
        solved, precis, reached = _newton(
            model, state, rtol, atol, float(ctol), count,
            0 if bandup is None else int(bandup),
            0 if banddown is None else int(banddown),
            banded, positivity, indices,
        )
    out = SteadyResult(solved, precis, reached, names if ynames else None)
    if verbose:
        print("precision at each steady state step")
        print(precis)
    return out


def _newton_user(model, jacobian, y, rtol, atol, ctol, maxiter, positivity,
                 indices):
    """Newton with a user Jacobian. ``jacobian`` returns ``(alpha, beta)``."""
    state = np.array(y, dtype=float, copy=True)
    precis = []
    reached = False
    for k in range(1, int(maxiter) + 1):
        ewt = _weights(state, rtol, atol)
        alpha, beta = jacobian(state)
        precis.append(float(np.mean(np.abs(beta))))
        if float(np.max(np.abs(beta / ewt))) <= 1.0:
            reached = True
            break
        delta = _solve_full(alpha, beta)
        if delta is None:
            break
        relative = float(np.max(np.abs(delta)))
        state = state + delta
        _clamp(state, positivity, indices)
        if relative <= ctol:
            reached = True
            if k < int(maxiter):
                residual = np.asarray(model(state), dtype=float)
                precis.append(float(np.mean(np.abs(residual))))
            break
    if not reached:
        warnings.warn("steady-state not reached", stacklevel=3)
    return state, precis, reached


def stodes(y, times=0, func=None, parms=None, rtol=1e-6, atol=1e-8,
           ctol=1e-8, sparsetype="sparseint", verbose=False, nnz=None,
           positive=False, maxiter=100, ynames=True, dllname=None, **kwargs):
    """Sparse steady state. The Newton step uses a full difference Jacobian.

    The Fortran sparse factorisation and this dense factorisation agree
    inside 1e-8 on the banded linear systems ``steady.1D`` and
    ``steady.2D`` solve. ``sparsetype`` is accepted and checked.
    """
    if func is None:
        raise ValueError(
            "`func' must be a function or character vector or a compiled function"
        )
    allowed = {
        "sparseint", "sparse", "sparsereturn", "1D", "2D", "3D",
        "2Dmap", "3Dmap",
    }
    if sparsetype not in allowed:
        raise ValueError(
            "'sparsetype' must be one of 'sparseint', 'sparse', '1D', '2D', '3D'"
        )
    if kwargs.get("jacfunc") is not None or (
        sparsetype == "sparse" and kwargs.get("jacfunc") is not None
    ):
        raise ValueError("jacfunc can not be used when jactype='sparse'")
    return stode(
        y, times=times, func=func, parms=parms, rtol=rtol, atol=atol,
        ctol=ctol, jactype="fullint", verbose=verbose, positive=positive,
        maxiter=maxiter, ynames=ynames, dllname=dllname, **{
            key: value for key, value in kwargs.items() if key != "jacfunc"
        },
    )


def runsteady(y, times=None, func=None, parms=None, stol=1e-8, rtol=1e-6,
              atol=1e-6, jacfunc=None, jactype="fullint", verbose=False,
              tcrit=None, hmin=0, hmax=None, hini=0, ynames=True,
              maxord=None, bandup=None, banddown=None, maxsteps=100000,
              dllname=None, time=None, **kwargs):
    """Integrate until the mean absolute derivative is below ``stol``."""
    from scipy.integrate import solve_ivp

    if func is None:
        raise ValueError(
            "`func' must be a function or character vector or a compiled function"
        )
    if time is not None and times is None:
        times = time
    if times is None:
        times = [0.0, math.inf]
    span = np.atleast_1d(_numeric(times, "times")).reshape(-1)
    if span.size == 1:
        span = np.array([float(span[0]), math.inf])
    state, names = _state(y)
    _check_solver_args(state, func, 1, rtol, atol, stol, dllname)
    start = float(span[0])
    end = float(span[-1])
    if math.isinf(end):
        end = 1e6
    label = "'func() ("

    def ode(t, current):
        result = _call_model(
            func, t, current, parms, names if ynames else None, kwargs,
        )
        rates, _extras = _as_rates(result, len(current), label)
        return rates

    def crossed(t, current):
        rate = np.asarray(ode(t, current), dtype=float)
        return float(np.mean(np.abs(rate))) - float(stol)

    crossed.terminal = True
    crossed.direction = -1
    # DLSODE's last step can sit about stol away from the root. A tighter
    # step lands on the first crossing of stol, which is the C loop's test.
    int_rtol = min(float(np.min(np.atleast_1d(np.asarray(rtol, dtype=float)))), 1e-12)
    int_atol = min(float(np.min(np.atleast_1d(np.asarray(atol, dtype=float)))), 1e-14)
    options = {
        "rtol": int_rtol, "atol": int_atol, "method": "LSODA", "events": crossed,
        "dense_output": True,
    }
    if hmax is not None:
        options["max_step"] = float(hmax)
    if tcrit is not None:
        end = min(end, float(tcrit))
    initial = np.asarray(ode(start, state), dtype=float)
    if float(np.mean(np.abs(initial))) < float(stol):
        out = SteadyResult(state, [float(np.mean(np.abs(initial)))], True,
                           names if ynames else None)
        out.time = start
        out.steps = 0
        return out
    solution = solve_ivp(ode, (start, end), state, **options)
    reached = solution.t_events is not None and len(solution.t_events[0]) > 0
    if reached:
        # A step can cross the whole tolerance band. Bisect for the
        # first time the mean absolute derivative falls below stol.
        when = float(solution.t_events[0][0])
        lo = start
        hi = when
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            rate = np.asarray(ode(mid, solution.sol(mid)), dtype=float)
            if float(np.mean(np.abs(rate))) <= float(stol):
                hi = mid
            else:
                lo = mid
        when = hi
        final = np.asarray(solution.sol(when), dtype=float)
    else:
        final = np.asarray(solution.y[:, -1], dtype=float)
        when = float(solution.t[-1])
    residual = np.asarray(ode(when, final), dtype=float)
    mean_abs = float(np.mean(np.abs(residual)))
    out = SteadyResult(final, [mean_abs], reached and mean_abs < float(stol) * 10,
                       names if ynames else None)
    # The C loop sets the flag when the mean has crossed stol.
    out.steady = bool(reached)
    out.time = when
    out.steps = int(solution.nfev)
    if verbose:
        print("mean residual derivative", mean_abs)
    return out


def steady(y, times=None, func=None, parms=None, method="stode", time=None,
           **kwargs):
    """Dispatch to ``stode``, ``stodes``, or ``runsteady``."""
    if method not in ("stode", "stodes", "runsteady"):
        raise ValueError(
            " 'method' should be one of 'stode', 'stodes', 'runsteady'"
        )
    if time is not None and times is None:
        times = time
    state, names = _state(y)
    if times is None:
        times = 0 if method in ("stode", "stodes") else [0, math.inf]
    if method == "stode":
        out = stode(y, times=times, func=func, parms=parms, **kwargs)
    elif method == "stodes":
        out = stodes(y, times=times, func=func, parms=parms, **kwargs)
    else:
        out = runsteady(y, times=times, func=func, parms=parms, **kwargs)
    out.classes = ["steady", "rootSolve", "list"]
    out.nspec = len(state)
    out.ynames = names
    if names is not None:
        out.y.names = list(names)
    return out


def steady_band(y, times=0, func=None, parms=None, nspec=None, bandup=None,
                banddown=None, time=None, **kwargs):
    """Banded Newton. The default bandwidth is ``nspec`` on each side."""
    if time is not None and times is None:
        times = time
    state, names = _state(y)
    if nspec is None and bandup is None:
        raise ValueError("cannot run steady.band: bandup is not specified")
    if bandup is None:
        bandup = nspec
    if banddown is None:
        if nspec is None:
            raise ValueError("cannot run steady.band: banddown is not specified")
        banddown = nspec
    if bandup is None:
        raise ValueError("cannot run steady.band: bandup is not specified")
    if banddown is None:
        raise ValueError("cannot run steady.band: banddown is not specified")
    out = stode(
        state, times=times, func=func, parms=parms, bandup=bandup,
        banddown=banddown, jactype="bandint", **kwargs,
    )
    out.classes = ["steady", "rootSolve", "list"]
    out.nspec = nspec if nspec is not None else 1
    out.ynames = names
    return out


def _order_index(n, nspec, per_spec):
    """1-based reorder used by ``steady.1D`` (``ii`` or ``ij``)."""
    if per_spec:
        # as.vector(t(matrix(ncol = nspec, 1:N)))
        matrix = np.arange(1, n + 1).reshape((n // nspec, nspec), order="F")
    else:
        # as.vector(t(matrix(nrow = nspec, 1:N)))
        matrix = np.arange(1, n + 1).reshape((nspec, n // nspec), order="F")
    return matrix.T.reshape(-1, order="F").astype(int)


def steady_1d(y, times=None, func=None, parms=None, nspec=None, dimens=None,
              names=None, method="stode", jactype=None, cyclicBnd=None,
              bandwidth=1, time=None, **kwargs):
    """Steady state of a 1-D difference scheme."""
    if kwargs.get("jacfunc") is not None:
        raise ValueError(
            "cannot run steady.1D with jacfunc specified - remove jacfunc "
            "from call list"
        )
    if dimens is None and nspec is None:
        raise ValueError(
            "cannot run steady.1D: either nspec or dimens should be specified"
        )
    if time is not None and times is None:
        times = time
    state, state_names = _state(y)
    n = len(state)
    if nspec is None:
        nspec = n / dimens if not isinstance(dimens, (list, tuple)) else n / dimens
        nspec = int(n // int(dimens))
    elif n % int(nspec) != 0:
        raise ValueError(
            "cannot run steady.1D: nspec is not an integer fraction of "
            "number of state variables"
        )
    nspec = int(nspec)
    if names is not None and len(names) != nspec:
        raise ValueError("length of 'names' should equal 'nspec'")
    if cyclicBnd is not None:
        method = "stodes"
    if method == "stodes" and bandwidth != 1:
        raise ValueError(
            "cannot combine 'method = stodes' with 'bandwidth' not = 1"
        )
    if method not in ("stode", "stodes", "runsteady"):
        raise ValueError(
            " 'method' should be one of 'stode', 'stodes', 'runsteady'"
        )
    if times is None:
        times = 0
    if method == "runsteady" and np.atleast_1d(_numeric(times, "times")).size == 1:
        times = [float(np.atleast_1d(_numeric(times, "times"))[0]), math.inf]
    if isinstance(func, str):
        raise ValueError(
            "You need to specify the name of the dll or shared library "
            "where 'func' can be found (without extension)"
        )
    if nspec == 1 and method == "stode":
        out = steady_band(
            state, times=times, func=func, parms=parms, nspec=nspec,
            bandup=nspec * bandwidth, banddown=nspec * bandwidth, **kwargs,
        )
    elif method == "stodes":
        out = stodes(
            state, times=times, func=func, parms=parms,
            sparsetype="1D" if jactype is None else jactype, **kwargs,
        )
    else:
        if jactype is None:
            jactype = "bandint"
        ii = _order_index(n, nspec, True) - 1
        ij = _order_index(n, nspec, False) - 1

        def bmodel(time_value, solver_state, pars, **kw):
            ordered = np.asarray(solver_state.values, dtype=float)
            model_state = ordered[ij]
            result = func(
                float(time_value), Vector(model_state, None), pars, **kw,
            )
            rates, extras = _as_rates(result, n, "'func() (")
            rates = np.asarray(rates, dtype=float)
            return [rates[ii], *extras]

        solver_state = state[ii]
        common = dict(
            y=solver_state, times=times, func=bmodel, parms=parms,
            bandup=nspec * bandwidth, banddown=nspec * bandwidth,
            jactype=jactype,
        )
        if method == "stode":
            out = stode(**common, **kwargs)
        else:
            out = runsteady(**{k: v for k, v in common.items() if k != "jactype"},
                            **kwargs)
        restored = np.zeros(n)
        restored[ii] = np.asarray(out.y.values, dtype=float)
        out.y = Vector(restored, state_names)
    out.classes = ["steady1D", "rootSolve", "list"]
    boxes = n // nspec if dimens is None else int(dimens)
    out.dimens = boxes
    out.nspec = nspec
    out.ynames = list(names) if names is not None else None
    if names is not None:
        # matrix(ncol = nspec) keeps column-major storage, so the flat
        # vector is unchanged. The names label the species.
        out.y.names = None
    return out


def _dimens_of(dimens, expected, label):
    if dimens is None:
        raise ValueError(f"cannot run {label}: dimens should be specified")
    values = [int(item) for item in dimens]
    if len(values) != expected:
        if label == "steady.2D":
            raise ValueError(
                "cannot run steady.2D: dimens should contain 2 values"
            )
        raise ValueError(
            "cannot run steady.3D: 'dimens' should contain 3 values"
        )
    return values


def steady_2d(y, times=None, func=None, parms=None, nspec=None, dimens=None,
              names=None, method="stodes", jactype=None, cyclicBnd=None,
              time=None, **kwargs):
    """Steady state of a 2-D difference scheme. The default method is sparse."""
    if kwargs.get("jacfunc") is not None:
        raise ValueError(
            "cannot run steady.2D with jacfunc specified - remove jacfunc "
            "from call list"
        )
    values = _dimens_of(dimens, 2, "steady.2D")
    return _steady_nd(
        y, times, func, parms, nspec, values, names, method, jactype,
        cyclicBnd, 2, time, "steady2D", kwargs,
    )


def steady_3d(y, times=None, func=None, parms=None, nspec=None, dimens=None,
              names=None, method="stodes", jactype=None, cyclicBnd=None,
              time=None, **kwargs):
    """Steady state of a 3-D difference scheme. The default method is sparse."""
    if kwargs.get("jacfunc") is not None:
        raise ValueError(
            "cannot run steady.2D with jacfunc specified - remove jacfunc "
            "from call list"
        )
    values = _dimens_of(dimens, 3, "steady.3D")
    return _steady_nd(
        y, times, func, parms, nspec, values, names, method, jactype,
        cyclicBnd, 3, time, "steady3D", kwargs,
    )


def _steady_nd(y, times, func, parms, nspec, dimens, names, method, jactype,
               cyclic, ndim, time, class_name, kwargs):
    label = "steady.2D" if ndim == 2 else "steady.3D"
    if time is not None and times is None:
        times = time
    state, _names = _state(y)
    n = len(state)
    volume = int(np.prod(dimens))
    if volume == 0 or n % volume != 0:
        raise ValueError(
            f"cannot run {label}: dimensions are not an integer fraction "
            "of number of state variables"
        )
    if nspec is None:
        nspec = n // volume
    elif int(nspec) * volume != n:
        if ndim == 2:
            raise ValueError(
                "cannot run steady.2D: dimens[1]*dimens[2]*nspec is not "
                "equal to number of state variables"
            )
        raise ValueError(
            "cannot run steady.3D: dimens[1]*dimens[2]*dimens[3]*nspec is "
            "not equal to number of state variables"
        )
    nspec = int(nspec)
    if names is not None and len(list(names)) != nspec:
        raise ValueError("length of 'names' should equal 'nspec'")
    if method not in ("stodes", "runsteady"):
        raise ValueError(
            " 'method' should be one of 'stodes', 'runsteady'"
        )
    if times is None:
        times = 0
    if method == "runsteady" and np.atleast_1d(
        np.asarray(times, dtype=float)
    ).size == 1:
        times = [float(np.atleast_1d(np.asarray(times, dtype=float))[0]), math.inf]
    if cyclic is not None:
        cycle = [int(item) for item in np.atleast_1d(cyclic)]
        if cycle and max(cycle) > ndim:
            raise ValueError(
                f"cannot run {label}: cyclicBnd should be a vector or "
                f"number not exceeding {ndim}"
            )
    if method == "stodes":
        kind = f"{ndim}D" if jactype is None else jactype
        out = stodes(
            state, times=times, func=func, parms=parms, sparsetype=kind,
            **kwargs,
        )
    else:
        out = runsteady(
            state, times=times, func=func, parms=parms, **kwargs,
        )
    out.classes = [class_name, "rootSolve", "list"]
    out.dimens = list(dimens)
    out.nspec = nspec
    out.ynames = list(names) if names is not None else None
    return out


def _root_checks(start, maxiter, rtol, atol, ctol):
    state, names = _state(start)
    n = len(state)
    try:
        count = int(maxiter)
    except (TypeError, ValueError) as exc:
        raise ValueError("`maxiter' must be numeric") from exc
    if count < 1:
        raise ValueError("maxiter must be >=1")
    r = np.atleast_1d(_numeric(rtol, "rtol")).reshape(-1)
    a = np.atleast_1d(_numeric(atol, "atol")).reshape(-1)
    c = np.atleast_1d(_numeric(ctol, "ctol")).reshape(-1)
    if a.size > 1 and a.size != n:
        raise ValueError(
            "`atol' must either be a scalar, or as long as `start'"
        )
    if r.size > 1 and r.size != n:
        raise ValueError("`rtol' must either be a scalar, or as long as `y'")
    if c.size > 1:
        raise ValueError("`ctol' must be a scalar")
    return state, names, count


def _evaluate_root(f, x, parms, kwargs):
    if parms is None:
        value = f(Vector(x), **kwargs)
    else:
        value = f(Vector(x), parms, **kwargs)
    if isinstance(value, Vector):
        return np.asarray(value.values, dtype=float)
    return np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)


def multiroot(f, start, maxiter=100, rtol=1e-6, atol=1e-8, ctol=1e-8,
              useFortran=True, positive=False, jacfunc=None,
              jactype="fullint", verbose=False, bandup=1, banddown=1,
              parms=None, **kwargs):
    """Root of several equations. The default path is the Fortran Newton."""
    state, names, count = _root_checks(start, maxiter, rtol, atol, ctol)
    n = len(state)
    if useFortran:
        def wrapped(time, x, pars, **kw):
            if pars is None:
                return [_evaluate_root(f, x.values, None, kw)]
            return [_evaluate_root(f, x.values, pars, kw)]

        if jactype == "sparse":
            solved = stodes(
                state, times=0, func=wrapped, parms=parms, atol=atol,
                rtol=rtol, ctol=ctol, maxiter=count, verbose=verbose,
                positive=positive, ynames=False,
            )
        else:
            solved = steady(
                state, times=0, func=wrapped, parms=parms, atol=atol,
                rtol=rtol, ctol=ctol, maxiter=count, method="stode",
                jacfunc=jacfunc, jactype=jactype, verbose=verbose,
                positive=positive, bandup=bandup, banddown=banddown,
                ynames=False,
            )
        root = np.asarray(solved.y.values, dtype=float)
        f_root = _evaluate_root(f, root, parms, kwargs)
        return MultiRoot(root, f_root, len(solved.precis), solved.precis[-1], names)

    # The R loop ignores jacfunc. A step smaller than ctol is not applied.
    x = np.array(state, dtype=float, copy=True)
    f_root = _evaluate_root(f, x, parms, kwargs)
    if len(f_root) != n:
        raise ValueError(
            "'f', function must return as many function values as elements in start"
        )
    precis = []
    from rootSolve._vec import perturb

    iterations = count
    for i in range(1, count + 1):
        iterations = i
        reference = np.array(x, dtype=float, copy=True)
        precis.append(float(np.mean(np.abs(f_root))))
        ewt = _weights(x, rtol, atol)
        if float(np.max(np.abs(f_root / ewt))) < 1.0:
            break
        steps = perturb(x)
        jacob = np.zeros((n, n))
        for column in range(n):
            x[column] = x[column] + steps.values[column]
            shifted = _evaluate_root(f, x, parms, kwargs)
            jacob[:, column] = (shifted - f_root) / steps.values[column]
            x[column] = reference[column]
        change = np.linalg.solve(jacob, -f_root)
        if float(np.max(np.abs(change))) < float(ctol):
            break
        x = x + change
        f_root = _evaluate_root(f, x, parms, kwargs)
    return MultiRoot(x, f_root, iterations, precis[-1], names)


def multiroot_1d(f, start, maxiter=100, rtol=1e-6, atol=1e-8, ctol=1e-8,
                 nspec=None, dimens=None, verbose=False, positive=False,
                 names=None, parms=None, **kwargs):
    """Root of a 1-D system, through ``steady.1D``."""
    state, state_names, count = _root_checks(start, maxiter, rtol, atol, ctol)

    def wrapped(time, x, pars, **kw):
        if pars is None:
            return [_evaluate_root(f, x.values, None, kw)]
        return [_evaluate_root(f, x.values, pars, kw)]

    solved = steady_1d(
        state, times=0, func=wrapped, parms=parms, atol=atol, rtol=rtol,
        ctol=ctol, positive=positive, method="stode", nspec=nspec,
        dimens=dimens, names=names, maxiter=count, verbose=verbose, **kwargs,
    )
    root = np.asarray(solved.y.values, dtype=float)
    f_root = _evaluate_root(f, root, parms, kwargs)
    return MultiRoot(
        root, f_root, len(solved.precis), solved.precis[-1],
        state_names if names is None else names,
    )
