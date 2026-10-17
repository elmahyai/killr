"""Option table and the defaults nloptr fills in before it calls NLopt."""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np

_TABLE = json.loads(
    (Path(__file__).resolve().parent / "default_options.json").read_text()
)
_BY_NAME = {row["name"]: row for row in _TABLE}

# is.nloptr accepts ESCH. The option table's algorithm list does not.
ALGORITHMS = [
    "NLOPT_GN_DIRECT",
    "NLOPT_GN_DIRECT_L",
    "NLOPT_GN_DIRECT_L_RAND",
    "NLOPT_GN_DIRECT_NOSCAL",
    "NLOPT_GN_DIRECT_L_NOSCAL",
    "NLOPT_GN_DIRECT_L_RAND_NOSCAL",
    "NLOPT_GN_ORIG_DIRECT",
    "NLOPT_GN_ORIG_DIRECT_L",
    "NLOPT_GD_STOGO",
    "NLOPT_GD_STOGO_RAND",
    "NLOPT_LD_SLSQP",
    "NLOPT_LD_LBFGS",
    "NLOPT_LN_PRAXIS",
    "NLOPT_LD_VAR1",
    "NLOPT_LD_VAR2",
    "NLOPT_LD_TNEWTON",
    "NLOPT_LD_TNEWTON_RESTART",
    "NLOPT_LD_TNEWTON_PRECOND",
    "NLOPT_LD_TNEWTON_PRECOND_RESTART",
    "NLOPT_GN_CRS2_LM",
    "NLOPT_GN_MLSL",
    "NLOPT_GD_MLSL",
    "NLOPT_GN_MLSL_LDS",
    "NLOPT_GD_MLSL_LDS",
    "NLOPT_LD_MMA",
    "NLOPT_LD_CCSAQ",
    "NLOPT_LN_COBYLA",
    "NLOPT_LN_NEWUOA",
    "NLOPT_LN_NEWUOA_BOUND",
    "NLOPT_LN_NELDERMEAD",
    "NLOPT_LN_SBPLX",
    "NLOPT_LN_AUGLAG",
    "NLOPT_LD_AUGLAG",
    "NLOPT_LN_AUGLAG_EQ",
    "NLOPT_LD_AUGLAG_EQ",
    "NLOPT_LN_BOBYQA",
    "NLOPT_GN_ISRES",
    "NLOPT_GN_ESCH",
]

EQ_ALGORITHMS = [
    "NLOPT_LD_AUGLAG",
    "NLOPT_LN_AUGLAG",
    "NLOPT_LD_AUGLAG_EQ",
    "NLOPT_LN_AUGLAG_EQ",
    "NLOPT_GN_ISRES",
    "NLOPT_LD_SLSQP",
    "NLOPT_LN_COBYLA",
]

LOCAL_ALGORITHMS = [
    "NLOPT_LD_AUGLAG",
    "NLOPT_LN_AUGLAG",
    "NLOPT_LD_AUGLAG_EQ",
    "NLOPT_LN_AUGLAG_EQ",
    "NLOPT_GN_MLSL",
    "NLOPT_GD_MLSL",
    "NLOPT_GN_MLSL_LDS",
    "NLOPT_GD_MLSL_LDS",
]


def get_default_options():
    """Rows of the option table, in the order nloptr prints them."""
    return [dict(row) for row in _TABLE]


def _r_character(value) -> str:
    """R's as.character for the scalars that show up in termination text."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, np.ndarray)):
        return " ".join(_r_character(item) for item in np.ravel(value))
    number = float(value)
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    if number == 0.0:
        return "-0" if math.copysign(1.0, number) < 0 else "0"
    absolute = abs(number)
    exponent = math.floor(math.log10(absolute))
    if exponent < -3 or exponent >= 5:
        digits = f"{absolute:.15e}".split("e")
        mantissa = digits[0].rstrip("0").rstrip(".")
        if mantissa == "":
            mantissa = "0"
        sign = "-" if number < 0 else ""
        power = int(digits[1])
        return f"{sign}{mantissa}e{power:+03d}"
    text = f"{number:.15g}"
    if "e" in text or "E" in text:
        return _r_character(number) if False else text
    return text


def _eval_default(text: str, x0, n_ineq: int, n_eq: int):
    if text == "none":
        return "none"
    if text == "all":
        return "all"
    if text == "FALSE":
        return False
    if text == "TRUE":
        return True
    if text == "-Inf":
        return float("-inf")
    if text == "rep(0.0, length(x0))":
        return np.zeros(len(np.atleast_1d(x0)), dtype=float)
    if text == "rep(1e-8, num_constraints_ineq)":
        return np.full(n_ineq, 1e-8)
    if text == "rep(1e-8, num_constraints_eq)":
        return np.full(n_eq, 1e-8)
    if _BY_NAME and text.replace(".", "", 1).replace("-", "", 1).replace("e", "", 1).replace("+", "", 1).isdigit() or _is_number(text):
        number = float(text)
        row_type = None
        return number
    return float(text)


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def add_default_options(opts_user, x0=0, num_constraints_ineq=0, num_constraints_eq=0):
    """Fill every option, and describe the termination test the user named."""
    user = {} if opts_user is None else dict(opts_user)
    termination_names = [
        row["name"] for row in _TABLE if row["is_termination_condition"]
    ]
    named = [name for name in user if name in termination_names and user[name] is not None]
    if not named:
        xtol = float(_BY_NAME["xtol_rel"]["default"])
        warnings.warn(
            "No termination criterion specified, using default"
            f"(relative x-tolerance = {_r_character(xtol)})",
            stacklevel=2,
        )
        termination = f"relative x-tolerance = {_r_character(xtol)} (DEFAULT)"
    else:
        pieces_names = " ".join(named)
        pieces_values = " ".join(_r_character(user[name]) for name in named)
        termination = f"{pieces_names}: {pieces_values}"

    filled = {}
    for row in _TABLE:
        name = row["name"]
        if name in user and user[name] is not None:
            filled[name] = user[name]
        elif row["type"] == "character":
            filled[name] = row["default"]
        else:
            filled[name] = _eval_default(
                row["default"], x0, num_constraints_ineq, num_constraints_eq
            )
            if row["type"] == "integer":
                filled[name] = _as_integer(filled[name])
            elif row["type"] == "logical":
                filled[name] = bool(filled[name])
    return {"opts_user": filled, "termination_conditions": termination}


def _as_integer(value) -> int:
    if isinstance(value, bool) or value is None:
        return -2147483648
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return -2147483648
    truncated = math.trunc(number)
    if truncated < -2147483648 or truncated > 2147483647:
        return -2147483648
    return int(truncated)


def nl_opts(optlist=None):
    """Defaults used by the algorithm wrappers. `algorithm` is left empty."""
    opts = {
        "stopval": float("-inf"),
        "xtol_rel": 1e-6,
        "maxeval": 1000,
        "ftol_rel": 0.0,
        "ftol_abs": 0.0,
        "check_derivatives": False,
        "algorithm": None,
    }
    if optlist is None:
        return opts
    if not isinstance(optlist, dict) or "" in optlist:
        raise ValueError("Argument `optlist` must be a named list.")
    for name, value in optlist.items():
        opts[name] = value
    if opts.get("algorithm") is not None:
        warnings.warn("Option `algorithm` cannot be set here. It will be overwritten.")
        opts["algorithm"] = None
    return opts


def _wrap_text(text: str, width: int) -> list[str]:
    """R strwrap. Each word is counted with a trailing space, so a full line stops one short of width."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current: list[str] = []
    used = 0
    for word in words:
        needed = len(word) + 1
        if current and used + needed > width:
            lines.append(" ".join(current))
            current = [word]
            used = needed
        else:
            current.append(word)
            used += needed
    if current:
        lines.append(" ".join(current))
    return lines


def print_options(opts_show=None, opts_user=None) -> None:
    """Print the option table the way nloptr.print.options does."""
    rows = get_default_options()
    if opts_show is not None:
        wanted = set(opts_show)
        rows = [row for row in rows if row["name"] in wanted]
    for row in rows:
        print(row["name"])
        values = _wrap_text(row["possible_values"], 50)
        print("\tpossible values: " + values[0])
        for extra in values[1:]:
            print("\t         " + extra)
        print(f"\tdefault value:   {row['default']}")
        if opts_user is not None:
            current = opts_user.get(row["name"], None)
            shown = "(default)" if current is None else current
            print(f"\tcurrent value:   {shown}")
        description = _wrap_text(row["description"], 70)
        print()
        for line in description:
            print("\t" + line)
        print()
