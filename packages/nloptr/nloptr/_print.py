"""Print an nloptr result in the same paragraphs as print.nloptr."""

from __future__ import annotations

import math

import numpy as np


def _character(number: float) -> str:
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    absolute = abs(number)
    if number == 0.0:
        return "-0" if math.copysign(1.0, number) < 0 else "0"
    exponent = math.floor(math.log10(absolute))
    if exponent < -3 or exponent >= 5:
        mantissa, power = f"{absolute:.15e}".split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        sign = "-" if number < 0 else ""
        return f"{sign}{mantissa}e{int(power):+03d}"
    return f"{number:.15g}"


def _cat_controls(values) -> str:
    parts = []
    for value in np.ravel(np.asarray(values, dtype=float)):
        parts.append(format(float(value), ".7g"))
    return " ".join(parts)


def print_nloptr(x, show_controls=True, **_ignored) -> None:
    """Print the result of a minimization."""
    call = x.get("call")
    if call is None:
        call = "nloptr(...)"
    print(f"\nCall:\n{call}\n")
    print(f"Minimization using NLopt version {x['version']} \n")
    print(f"NLopt solver status: {x['status']} ( {x['message']} )")
    print(f"Number of Iterations....: {x['iterations']} ")
    print(f"Termination conditions:  {x['termination_conditions']} ")
    print(f"Number of inequality constraints:  {x['num_constraints_ineq']} ")
    print(f"Number of equality constraints:    {x['num_constraints_eq']} ")
    controls = np.asarray(x["solution"], dtype=float)
    indices = np.arange(len(controls))
    show = show_controls
    if isinstance(show_controls, (bool, np.bool_)) and show_controls:
        indices = np.arange(len(controls))
    if isinstance(show_controls, (list, tuple, np.ndarray)) and not isinstance(show_controls, bool):
        indices = np.asarray(show_controls, dtype=int) - 1
        show = True
    if not isinstance(show, (bool, np.bool_)):
        show = True
    success = 1 <= int(x["status"]) <= 4
    label = "Optimal" if success else "Current"
    print(f"{label} value of objective function:  {_character(float(x['objective']))} ")
    if show:
        chosen = controls[indices]
        if len(indices) < len(controls):
            print(f"{label} value of user-defined subset of controls: ", end="")
        else:
            print(f"{label} value of controls: ", end="")
        print(_cat_controls(chosen))
        print()
    print()
