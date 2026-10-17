"""Print integrator diagnostics for a deSolve result (``diagnostics.deSolve``)."""

from __future__ import annotations

import math
import sys
from typing import Any, Sequence

import numpy as np

from deSolve.rk4 import DeSolveMatrix, _ISTATE_TEXT

_RSTATE_TEXT = (
    "The step size in t last used (successfully):",
    "The step size to be attempted on the next step:",
    "The current value of the independent variable which the solver has reached:",
    "Tolerance scale factor > 1.0 computed when requesting too much accuracy:",
    "The value of t at the time of the last method switch, if any:",
)

_MEBDFI_ISTATE = (
    "The number of backsolves so far",
    "The number of times a new coefficient matrix has been formed so far",
    "The number of times the order of the method has been changed so far",
)


def _signif(x: float, digits: int = 7) -> float:
    if x == 0.0 or not math.isfinite(x):
        return float(x)
    power = math.floor(math.log10(abs(x)))
    return float(round(x, int(digits - 1 - power)))


def _format_signif(value: Any, digits: int = 7) -> str:
    if value is None:
        return "NA"
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (list, tuple, np.ndarray)):
        parts = [_format_signif(item, digits=digits) for item in np.asarray(value).reshape(-1)]
        return " ".join(parts)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return str(number)
    rounded = _signif(number, digits)
    if rounded == 0.0 and number != 0.0:
        return str(number)
    if float(int(rounded)) == rounded and abs(rounded) < 1e15:
        return str(int(rounded)) if rounded == int(rounded) else str(rounded)
    text = str(rounded)
    if "e" not in text and "." not in text:
        return text
    return text.rstrip("0").rstrip(".") if "." in text else text


def _printmessage(messages: Sequence[str], state: Sequence[Any], nr: Sequence[int] | None = None) -> None:
    if nr is None:
        nr = list(range(1, len(messages) + 1))
    lines = [
        f"{num:2d} {message} {_format_signif(value)} \n"
        for num, message, value in zip(nr, messages, state, strict=False)
    ]
    # ``cat("\\n", paste(...), "\\n")`` uses the default ``sep = " "`` between arguments.
    sys.stdout.write("\n ")
    for index, line in enumerate(lines):
        if index:
            sys.stdout.write(" ")
        sys.stdout.write(line)
    sys.stdout.write(" \n")


def _printidid(idid: int) -> None:
    sys.stdout.write(f"\n  return code (idid) =  {idid} \n")
    if idid == 2 or idid == 0:
        sys.stdout.write("  Integration was successful.\n")
    elif idid == 3:
        sys.stdout.write(
            "  Integration was successful and a root was found before reaching the end.\n"
        )
    elif idid == -1:
        sys.stdout.write(
            "  Excess work done on this call. (Perhaps wrong Jacobian type MF.)\n"
        )
    elif idid == -2:
        sys.stdout.write("  Excess accuracy requested. (Tolerances too small.)\n")
    elif idid == -3:
        sys.stdout.write("  Illegal input detected. (See printed message.)\n")
    elif idid == -4:
        sys.stdout.write("  Repeated error test failures. (Check all input.)\n")
    elif idid == -5:
        sys.stdout.write(
            "  Repeated convergence failures. (Perhaps bad Jacobian supplied or wrong choice of MF or tolerances.)\n"
        )
    elif idid == -6:
        sys.stdout.write(
            "  Error weight became zero during problem. (Solution component i vanished, and ATOL or ATOL(i) = 0.)\n"
        )
    elif idid == -7:
        sys.stdout.write("  Work space insufficient to finish (see messages).\n")
    elif idid == -8:
        sys.stdout.write(
            "  A fatal error came from sparse solver CDRV by way of DPRJS or DSOLSS.\n"
        )


def _printidid_daspk(idid: int) -> None:
    sys.stdout.write(f"\n  return code (idid) =  {idid} \n")
    if idid > 0:
        sys.stdout.write("  integration was succesful\n")
        if idid == 1:
            sys.stdout.write(
                "  A step was successfully taken in the intermediate-output mode.  The code has not yet reached TOUT.\n"
            )
        if idid == 2:
            sys.stdout.write(
                "  The integration to TSTOP was successfully completed (T = TSTOP) by stepping exactly to TSTOP.\n"
            )
        if idid == 3:
            sys.stdout.write(
                "  The integration to TOUT was successfully completed (T = TOUT) by stepping past TOUT. Y(*) and YPRIME(*) are obtained by interpolation.\n"
            )
        if idid == 4:
            sys.stdout.write(
                "  The initial condition calculation, with INFO(11) > 0, was successful, and INFO(14) = 1. No integration steps were taken, and the solution is not considered to have been started.\n"
            )
    elif idid < 0 and idid > -33:
        sys.stdout.write("  integration was interrupted\n")
        if idid == -1:
            sys.stdout.write("  A large amount of work has been expended (about 500 steps).\n")
        elif idid == -2:
            sys.stdout.write("  The error tolerances are too stringent.\n")
        elif idid == -3:
            sys.stdout.write(
                "  The local error test cannot be satisfied because a zero component in ATOL was specified and the corresponding computed solution component is zero.  Thus, a pure relative error test is impossible for this component.\n"
            )
        elif idid == -5:
            sys.stdout.write(
                "  There were repeated failures in the evaluation or processing of the preconditioner (in jacfunc).\n"
            )
        elif idid == -6:
            sys.stdout.write("  DDASPK had repeated error test failures on the last attempted step.\n")
        elif idid == -7:
            sys.stdout.write(
                "  The nonlinear system solver in the time integration could not converge.\n"
            )
        elif idid == -8:
            sys.stdout.write(
                "  The matrix of partial derivatives appears to be singular (direct method).\n"
            )
        elif idid == -9:
            sys.stdout.write(
                "  The nonlinear system solver in the time integration failed to achieve convergence, and there were repeated error test failures in this step.\n"
            )
        elif idid == -10:
            sys.stdout.write(
                "  The nonlinear system solver in the time integration failed to achieve convergence because IRES was equal to -1.\n"
            )
        elif idid == -11:
            sys.stdout.write(
                "  IRES = -2 was encountered and control is being returned to the calling program.\n"
            )
        elif idid == -12:
            sys.stdout.write("  DDASPK failed to compute the initial Y, YPRIME.\n")
        elif idid == -13:
            sys.stdout.write(
                "  Unrecoverable error encountered inside user's PSOL routine, and control is being returned to the calling program.\n"
            )
        elif idid == -14:
            sys.stdout.write("  The Krylov linear system solver could not achieve convergence.\n")
    elif idid == -33:
        sys.stdout.write("  integration was terminated\n")
        sys.stdout.write(
            "  The code has encountered trouble from which it cannot recover.  A message is printed explaining the trouble and control is returned to the calling program.\n"
        )


def _istate_labels(name: str) -> tuple[str, ...]:
    labels = list(_ISTATE_TEXT)
    if name == "mebdfi":
        labels[18:21] = list(_MEBDFI_ISTATE)
    return tuple(labels)


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, np.floating) and np.isnan(value):
        return True
    return False


def _print_istate(istate: Sequence[Any], name: str, *, full: bool) -> None:
    labels = _istate_labels(name)
    sys.stdout.write("\n--------------------\n")
    sys.stdout.write("INTEGER values\n")
    sys.stdout.write("--------------------\n")
    if full:
        indices = list(range(1, 20))
    else:
        indices = [index + 1 for index, value in enumerate(istate) if not _is_na(value)]
    picked_labels = [labels[index - 1] for index in indices]
    picked_values = [istate[index - 1] for index in indices]
    _printmessage(picked_labels, picked_values, nr=indices)


def _print_rstate(rstate: Sequence[Any] | None) -> None:
    if rstate is None:
        return
    sys.stdout.write("--------------------\n")
    sys.stdout.write("RSTATE values\n")
    sys.stdout.write("--------------------\n")
    indices = [index + 1 for index, value in enumerate(rstate) if not _is_na(value)]
    if not indices:
        return
    picked_labels = [_RSTATE_TEXT[index - 1] for index in indices]
    picked_values = [rstate[index - 1] for index in indices]
    _printmessage(picked_labels, picked_values, nr=indices)


def _object_attrs(obj: Any) -> dict[str, Any]:
    if isinstance(obj, DeSolveMatrix):
        return {
            "type": getattr(obj, "type", None),
            "istate": getattr(obj, "istate", None),
            "rstate": getattr(obj, "rstate", None),
            "nroot": getattr(obj, "nroot", None),
            "troot": getattr(obj, "troot", None),
            "iroot": getattr(obj, "iroot", None),
        }
    attrs = getattr(obj, "attributes", None)
    if isinstance(attrs, dict):
        return attrs
    return {
        "type": getattr(obj, "type", None),
        "istate": getattr(obj, "istate", None),
        "rstate": getattr(obj, "rstate", None),
        "nroot": getattr(obj, "nroot", None),
        "troot": getattr(obj, "troot", None),
        "iroot": getattr(obj, "iroot", None),
    }


def diagnostics_deSolve(obj, Full: bool = False, **kwargs):
    """Print return codes and istate or rstate diagnostics for a deSolve object."""
    del kwargs
    attr = _object_attrs(obj)
    name = attr.get("type")
    istate = attr.get("istate")
    rstate = attr.get("rstate")

    sys.stdout.write("\n--------------------\n")
    sys.stdout.write(f"{name} return code")
    sys.stdout.write("\n--------------------\n")

    idid = istate[0]
    if name == "lsodes" and idid == -7:
        idid = -8
    if name == "rk":
        pass  # R references printidid_rk without calling it
    if name == "daspk":
        _printidid_daspk(int(idid))
    else:
        _printidid(int(idid))

    _print_istate(istate, name, full=bool(Full))

    if name != "rk":
        _print_rstate(rstate)

    nroot = attr.get("nroot")
    troot = attr.get("troot")
    iroot_attr = attr.get("iroot")

    if nroot is not None:
        sys.stdout.write("--------------------\n")
        sys.stdout.write("ROOT + event \n")
        sys.stdout.write("--------------------\n")
        sys.stdout.write(
            f"\n root found at times : {_format_signif(troot, digits=5)} \n"
        )

    iroot = None
    if name == "lsodar" or (name in ("lsode", "lsodes", "radau") and iroot_attr is not None):
        sys.stdout.write("--------------------\n")
        sys.stdout.write("ROOT\n")
        sys.stdout.write("--------------------\n")
        if iroot_attr is not None:
            iroot = [index + 1 for index, flag in enumerate(iroot_attr) if flag == 1]
        else:
            iroot = []
        if iroot:
            sys.stdout.write(
                f"\n root found for root equation: {_format_signif(iroot, digits=0)} \n"
            )
            sys.stdout.write(f"\n at time : {_format_signif(troot, digits=5)} \n")
        elif nroot is None:
            sys.stdout.write("\n NO root found \n")
        return {"istate": istate, "rstate": rstate, "iroot": iroot}

    return {"istate": istate, "rstate": rstate}
