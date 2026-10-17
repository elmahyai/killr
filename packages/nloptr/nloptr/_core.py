"""The nloptr solver. NLopt 2.10.0 does the minimization."""

from __future__ import annotations

import inspect
import math
import sys

import nlopt
import numpy as np

from nloptr._finite import check_derivatives
from nloptr._options import (
    ALGORITHMS,
    EQ_ALGORITHMS,
    LOCAL_ALGORITHMS,
    add_default_options,
    get_default_options,
    print_options,
)

_STATUS = {
    1: "NLOPT_SUCCESS: Generic success return value.",
    2: "NLOPT_STOPVAL_REACHED: Optimization stopped because stopval (above) was reached.",
    3: "NLOPT_FTOL_REACHED: Optimization stopped because ftol_rel or ftol_abs (above) was reached.",
    4: "NLOPT_XTOL_REACHED: Optimization stopped because xtol_rel or xtol_abs (above) was reached.",
    5: "NLOPT_MAXEVAL_REACHED: Optimization stopped because maxeval (above) was reached.",
    6: "NLOPT_MAXTIME_REACHED: Optimization stopped because maxtime (above) was reached.",
    -1: "NLOPT_FAILURE: Generic failure code.",
    -2: "NLOPT_INVALID_ARGS: Invalid arguments (e.g. lower bounds are bigger than upper bounds, an unknown algorithm was specified, etcetera).",
    -3: "NLOPT_OUT_OF_MEMORY: Ran out of memory.",
    -4: "NLOPT_ROUNDOFF_LIMITED: Roundoff errors led to a breakdown of the optimization algorithm. In this case, the returned minimum may still be useful. (e.g. this error occurs in NEWUOA if one tries to achieve a tolerance too close to machine precision.)",
    -5: "Return status not recognized.",
}


class NloptrResult(dict):
    """A solved problem. Fields match the list nloptr returns."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _stop(message: str) -> None:
    raise ValueError(message)


def _as_vector(x0) -> np.ndarray:
    if isinstance(x0, bool) or isinstance(x0, str):
        _stop("x0 must be numeric\n")
    try:
        values = np.asarray(x0, dtype=float)
    except (TypeError, ValueError):
        _stop("x0 must be numeric\n")
    if values.ndim == 0:
        values = values.reshape(1)
    values = np.array(values.reshape(-1), dtype=float, copy=True)
    return values


def _check_fun_args(fn, kwargs, funname: str) -> None:
    if fn is None:
        return
    if not callable(fn):
        _stop(f"{funname} must be a function\n")
    params = list(inspect.signature(fn).parameters.values())
    if len(params) <= 1:
        return
    rest = params[1:]
    if any(param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD) for param in rest):
        return
    required = [param.name for param in rest]
    for name in required:
        if name not in kwargs:
            _stop(
                f"{funname} requires argument '{name}' but this has not been "
                "passed to the 'nloptr' function.\n"
            )
    for name in kwargs:
        if name not in required:
            _stop(
                f"{name}' passed to (...) in 'nloptr' but this is not "
                f"required in the {funname} function.\n"
            )


def _call(fn, x, kwargs):
    if kwargs:
        return fn(x, **kwargs)
    return fn(x)


def _is_named_list(value) -> bool:
    return isinstance(value, dict)


def _first_real(value) -> float:
    return float(np.ravel(np.asarray(value, dtype=float))[0])


def _as_reals(value) -> np.ndarray:
    return np.atleast_1d(np.asarray(value, dtype=float).reshape(-1))


def _missing(value) -> bool:
    array = np.asarray(value, dtype=float)
    return bool(np.any(np.isnan(array)))


def _algorithm_kind(names: list[str], letter: str) -> list[str]:
    import re

    pattern = re.compile(rf"NLOPT_[{letter}]{letter and ''}")
    # R's grep("NLOPT_[G,L]D", ...) is a character class, not two letters.
    return names


def _split_algorithms(pattern: str) -> list[str]:
    import re

    row = next(row for row in get_default_options() if row["name"] == "algorithm")
    names = [part.strip() for part in row["possible_values"].split(",")]
    return [name for name in names if re.search(pattern, name)]


def _status_message(status: int) -> str:
    return _STATUS.get(int(status), "Return status not recognized.")


def _xtol_abs(value, n: int) -> np.ndarray:
    """The C side reads only the first element and copies it onto every control."""
    first = _first_real(value)
    return np.full(n, first)


def _apply(opt, opts, n: int) -> None:
    opt.set_stopval(float(opts["stopval"]))
    opt.set_ftol_rel(float(opts["ftol_rel"]))
    opt.set_ftol_abs(float(opts["ftol_abs"]))
    opt.set_xtol_rel(float(opts["xtol_rel"]))
    opt.set_xtol_abs(_xtol_abs(opts["xtol_abs"], n))
    opt.set_maxeval(int(opts["maxeval"]))
    opt.set_maxtime(float(opts["maxtime"]))
    opt.set_population(int(opts["population"]))
    opt.set_vector_storage(int(opts["vector_storage"]))
    seed = float(np.ravel(np.asarray(opts["ranseed"], dtype=float))[0])
    if seed > 0:
        nlopt.srand(int(seed))


def _make_opt(algorithm: str, n: int, opts) -> nlopt.opt:
    code = getattr(nlopt, algorithm.removeprefix("NLOPT_"))
    opt = nlopt.opt(code, n)
    _apply(opt, opts, n)
    return opt


def _jacobian(value, m: int, n: int) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim == 2:
        return array
    flat = array.reshape(-1)
    if m == 1:
        return flat.reshape(1, n)
    return flat.reshape((m, n), order="F")


def _objective_callback(fn, kwargs, counter, print_level):
    def objective(x, grad):
        counter[0] += 1
        if print_level >= 1:
            print(f"iteration: {counter[0]}")
        if print_level >= 3:
            if len(x) == 1:
                print(f"\tx = {x[0]:.6f}")
            else:
                body = ", ".join(f"{item:.6f}" for item in x)
                print(f"\tx = ({body})")
        value = _call(fn, x, kwargs)
        if _is_named_list(value):
            objective_value = _first_real(value["objective"])
            gradient = value.get("gradient")
        else:
            objective_value = _first_real(value)
            gradient = None
        if print_level >= 1:
            print(f"\tf(x) = {objective_value:.6f}")
        if grad.size > 0 and gradient is not None:
            grad[:] = _as_reals(gradient)
        return objective_value

    return objective


def _constraint_callback(fn, kwargs, print_level, label):
    def constraint(result, x, grad):
        value = _call(fn, x, kwargs)
        if _is_named_list(value):
            constraints = _as_reals(value["constraints"])
            jacobian = value.get("jacobian")
        else:
            constraints = _as_reals(value)
            jacobian = None
        result[:] = constraints
        if print_level >= 2:
            if len(constraints) == 1:
                print(f"\t{label}(x) = {constraints[0]:.6f}")
            else:
                body = ", ".join(f"{item:.6f}" for item in constraints)
                print(f"\t{label}(x) = ({body})")
        if grad.size > 0 and jacobian is not None:
            grad[:] = _jacobian(jacobian, len(constraints), len(x))

    return constraint


def is_nloptr(x) -> bool:
    """Return whether `x` is a fully specified nloptr problem."""
    if x is None or not isinstance(x, dict):
        return False
    x0 = _as_vector(x["x0"])
    if not callable(x["eval_f"]):
        _stop("eval_f is not a function")
    if x.get("eval_g_ineq") is not None and not callable(x["eval_g_ineq"]):
        _stop("eval_g_ineq is not a function")
    if x.get("eval_g_eq") is not None and not callable(x["eval_g_eq"]):
        _stop("eval_g_eq is not a function")
    if _missing(x0):
        _stop("x0 contains NA")
    lower = np.asarray(x["lower_bounds"], dtype=float).reshape(-1)
    upper = np.asarray(x["upper_bounds"], dtype=float).reshape(-1)
    if len(x0) != len(lower):
        _stop("length(lb) != length(x0)")
    if len(x0) != len(upper):
        _stop("length(ub) != length(x0)")
    if np.any(x0 < lower):
        _stop("at least one element in x0 < lb")
    if np.any(x0 > upper):
        _stop("at least one element in x0 > ub")

    algorithm = x["options"]["algorithm"]
    if algorithm not in ALGORITHMS:
        _stop(
            "Incorrect algorithm supplied. Use one of the following:\n"
            + "\n".join(ALGORITHMS)
        )
    derivative = _split_algorithms(r"NLOPT_[G,L]D")
    derivative_free = _split_algorithms(r"NLOPT_[G,L]N")
    f0 = x["eval_f"](x0)
    if _is_named_list(f0):
        if _missing(f0["objective"]):
            _stop("objective in x0 returns NA")
        if _missing(f0["gradient"]):
            _stop("gradient of objective in x0 returns NA")
        if len(_as_reals(f0["gradient"])) != len(x0):
            _stop("wrong number of elements in gradient of objective")
        if algorithm in derivative_free:
            import warnings

            warnings.warn(
                "a gradient was supplied for the objective function, "
                f"but algorithm {algorithm} does not use gradients."
            )
    else:
        if _missing(f0):
            _stop("objective in x0 returns NA")
        if algorithm in derivative:
            _stop(
                "A gradient for the objective function is needed by "
                f"algorithm {algorithm} but was not supplied.\n"
            )
    _check_constraint(x, "eval_g_ineq", "inequality", algorithm, derivative, derivative_free)
    _check_constraint(x, "eval_g_eq", "equality", algorithm, derivative, derivative_free)
    if x.get("num_constraints_eq", 0) > 0 and algorithm not in EQ_ALGORITHMS:
        _stop(
            "If you want to use equality constraints, then you should use one of "
            "these algorithms " + ", ".join(EQ_ALGORITHMS)
        )
    if algorithm in LOCAL_ALGORITHMS and x.get("local_options") is None:
        _stop(
            f"The algorithm {algorithm} needs a local optimizer; specify an "
            "algorithm and termination condition in local_opts"
        )
    ineq_tol = np.atleast_1d(np.asarray(x["options"]["tol_constraints_ineq"], dtype=float))
    if x.get("num_constraints_ineq", 0) != len(ineq_tol):
        _stop(
            "The vector tol_constraints_ineq in the options list has size "
            f"{len(ineq_tol)} which is unequal to the number of inequality "
            f"constraints, {x.get('num_constraints_ineq', 0)}."
        )
    eq_tol = np.atleast_1d(np.asarray(x["options"]["tol_constraints_eq"], dtype=float))
    if x.get("num_constraints_eq", 0) != len(eq_tol):
        _stop(
            "The vector tol_constraints_eq in the options list has size "
            f"{len(eq_tol)} which is unequal to the number of equality "
            f"constraints, {x.get('num_constraints_eq', 0)}."
        )
    return True


def _check_constraint(x, name, kind, algorithm, derivative, derivative_free):
    fn = x.get(name)
    if fn is None:
        return
    value = fn(x["x0"])
    if _is_named_list(value):
        if _missing(value["constraints"]):
            _stop(f"{kind} constraints in x0 returns NA")
        if _missing(value["jacobian"]):
            _stop(f"jacobian of {kind} constraints in x0 returns NA")
        constraints = _as_reals(value["constraints"])
        jacobian = np.asarray(value["jacobian"], dtype=float)
        expected = len(constraints) * len(_as_vector(x["x0"]))
        if jacobian.size != expected:
            _stop(
                f"wrong number of elements in jacobian of {kind} constraints "
                f"(is {jacobian.size}, but should be {len(constraints)} x "
                f"{len(_as_vector(x['x0']))} = {expected})"
            )
        if algorithm in derivative_free:
            import warnings

            warnings.warn(
                f"a gradient was supplied for the {kind} constraints, but "
                f"algorithm {algorithm} does not use gradients."
            )
    else:
        if _missing(value):
            _stop(f"{kind} constraints in x0 returns NA")
        if algorithm in derivative:
            _stop(
                f"A gradient for the {kind} constraints is needed by "
                f"algorithm {algorithm} but was not supplied.\n"
            )


def nloptr(
    x0,
    eval_f,
    eval_grad_f=None,
    lb=None,
    ub=None,
    eval_g_ineq=None,
    eval_jac_g_ineq=None,
    eval_g_eq=None,
    eval_jac_g_eq=None,
    opts=None,
    **kwargs,
):
    """Minimize a function with NLopt."""
    point = _as_vector(x0)
    if len(point) == 0:
        _stop("x0 must have length > 0\n")
    if not callable(eval_f):
        _stop("eval_f must be a function\n")
    _check_fun_args(eval_f, kwargs, "eval_f")
    _check_fun_args(eval_grad_f, kwargs, "eval_grad_f")
    _check_fun_args(eval_g_ineq, kwargs, "eval_g_ineq")
    _check_fun_args(eval_jac_g_ineq, kwargs, "eval_jac_g_ineq")
    _check_fun_args(eval_g_eq, kwargs, "eval_g_eq")
    _check_fun_args(eval_jac_g_eq, kwargs, "eval_jac_g_eq")

    lower = np.full(len(point), -np.inf) if lb is None else _as_vector(lb)
    upper = np.full(len(point), np.inf) if ub is None else _as_vector(ub)
    user_opts = {} if opts is None else dict(opts)

    probe = _call(eval_f, point, kwargs)
    if _is_named_list(probe) or eval_grad_f is None:
        eval_f_wrapper = lambda x: _call(eval_f, x, kwargs)
    else:
        def eval_f_wrapper(x):
            return {
                "objective": _call(eval_f, x, kwargs),
                "gradient": _call(eval_grad_f, x, kwargs),
            }

    eval_g_ineq_wrapper, n_ineq = _wrap_constraint(
        eval_g_ineq, eval_jac_g_ineq, point, kwargs
    )
    eval_g_eq_wrapper, n_eq = _wrap_constraint(eval_g_eq, eval_jac_g_eq, point, kwargs)

    local_opts = None
    if "local_opts" in user_opts and user_opts["local_opts"] is not None:
        local_filled = add_default_options(
            user_opts["local_opts"], point, n_ineq, n_eq
        )
        local_opts = local_filled["opts_user"]
        user_opts = dict(user_opts)
        user_opts.pop("local_opts", None)

    filled = add_default_options(user_opts, point, n_ineq, n_eq)
    options = filled["opts_user"]
    if options.get("print_options_doc"):
        print_options(opts_user=options)

    if options.get("check_derivatives"):
        listed = _split_algorithms(r"NLOPT_[G,L]N")
        if options["algorithm"] in listed:
            import warnings

            warnings.warn(
                "Skipping derivative checker because algorithm "
                f"'{options['algorithm']}' does not use gradients."
            )
        else:
            print("Checking gradients of objective function.", file=sys.stderr)
            check_derivatives(
                point,
                lambda x: eval_f_wrapper(x)["objective"],
                lambda x: eval_f_wrapper(x)["gradient"],
                check_derivatives_tol=options["check_derivatives_tol"],
                check_derivatives_print=options["check_derivatives_print"],
                func_grad_name="eval_grad_f",
            )
            if n_ineq > 0:
                print("Checking gradients of inequality constraints.\n", file=sys.stderr)
                check_derivatives(
                    point,
                    lambda x: eval_g_ineq_wrapper(x)["constraints"],
                    lambda x: eval_g_ineq_wrapper(x)["jacobian"],
                    check_derivatives_tol=options["check_derivatives_tol"],
                    check_derivatives_print=options["check_derivatives_print"],
                    func_grad_name="eval_jac_g_ineq",
                )
            if n_eq > 0:
                print("Checking gradients of equality constraints.\n", file=sys.stderr)
                check_derivatives(
                    point,
                    lambda x: eval_g_eq_wrapper(x)["constraints"],
                    lambda x: eval_g_eq_wrapper(x)["jacobian"],
                    check_derivatives_tol=options["check_derivatives_tol"],
                    check_derivatives_print=options["check_derivatives_print"],
                    func_grad_name="eval_jac_g_eq",
                )

    result = NloptrResult(
        x0=point,
        eval_f=eval_f_wrapper,
        lower_bounds=lower,
        upper_bounds=upper,
        num_constraints_ineq=n_ineq,
        eval_g_ineq=eval_g_ineq_wrapper,
        num_constraints_eq=n_eq,
        eval_g_eq=eval_g_eq_wrapper,
        options=options,
        local_options=local_opts,
        termination_conditions=filled["termination_conditions"],
        call=None,
    )
    is_nloptr(result)

    num_evals = 0
    solve = True
    while num_evals <= 10 and solve:
        num_evals += 1
        solution = _optimize(result)
        result.status = solution["status"]
        result.message = solution["message"]
        result.iterations = solution["iterations"]
        result.objective = solution["objective"]
        result.solution = solution["solution"]
        result.version = solution["version"]
        result["num.evals"] = num_evals
        if float(options["maxtime"]) > 0 or solution["status"] != 6:
            solve = False
    return result


def _wrap_constraint(fn, jac, point, kwargs):
    if fn is None:
        return None, 0
    probe = _call(fn, point, kwargs)
    if _is_named_list(probe) or jac is None:
        wrapper = lambda x: _call(fn, x, kwargs)
    else:
        def wrapper(x):
            return {
                "constraints": _call(fn, x, kwargs),
                "jacobian": _call(jac, x, kwargs),
            }
    sample = wrapper(point)
    if _is_named_list(sample):
        count = len(_as_reals(sample["constraints"]))
    else:
        count = len(_as_reals(sample))
    return wrapper, count


def _optimize(problem: NloptrResult) -> dict:
    n = len(problem["x0"])
    options = problem["options"]
    opt = _make_opt(options["algorithm"], n, options)
    if problem.get("local_options") is not None:
        local = _make_opt(problem["local_options"]["algorithm"], n, problem["local_options"])
        opt.set_local_optimizer(local)
    opt.set_lower_bounds(np.asarray(problem["lower_bounds"], dtype=float))
    opt.set_upper_bounds(np.asarray(problem["upper_bounds"], dtype=float))
    counter = [0]
    print_level = int(options["print_level"])
    opt.set_min_objective(
        _objective_callback(problem["eval_f"], {}, counter, print_level)
    )
    if problem["num_constraints_ineq"] > 0:
        tol = np.asarray(options["tol_constraints_ineq"], dtype=float).reshape(-1)
        opt.add_inequality_mconstraint(
            _constraint_callback(problem["eval_g_ineq"], {}, print_level, "g"),
            tol,
        )
    if problem["num_constraints_eq"] > 0:
        tol = np.asarray(options["tol_constraints_eq"], dtype=float).reshape(-1)
        opt.add_equality_mconstraint(
            _constraint_callback(problem["eval_g_eq"], {}, print_level, "h"),
            tol,
        )
    start = np.array(problem["x0"], dtype=float, copy=True)
    try:
        solved = opt.optimize(start)
    except Exception:
        solved = start
    status = int(opt.last_optimize_result())
    return {
        "status": status,
        "message": _status_message(status),
        "iterations": counter[0],
        "objective": float(opt.last_optimum_value()),
        "solution": np.asarray(solved, dtype=float).copy(),
        "version": f"{nlopt.version_major()}.{nlopt.version_minor()}.{nlopt.version_bugfix()}",
    }
