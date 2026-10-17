"""Control list for the Levenberg-Marquardt least squares algorithm."""

import math
import sys

import numpy as np

_MISSING = object()


def nls_lm_control(
    ftol=_MISSING,
    ptol=_MISSING,
    gtol=0.0,
    diag=_MISSING,
    epsfcn=0.0,
    factor=100.0,
    maxfev=_MISSING,
    maxiter=50.0,
    nprint=0.0,
):
    """Return the nine controls ``nls.lm`` reads.

    Defaults follow the installed function. ``maxfev`` is an empty integer
    vector, and ``diag`` is an empty list. ``nls.lm`` fills an empty
    ``maxfev`` later; this function stores the arguments as given.
    """
    if ftol is _MISSING:
        ftol = math.sqrt(sys.float_info.epsilon)
    if ptol is _MISSING:
        ptol = math.sqrt(sys.float_info.epsilon)
    if diag is _MISSING:
        diag = []
    if maxfev is _MISSING:
        maxfev = np.array([], dtype=np.int32)
    return NlsLmControl(
        ftol=ftol,
        ptol=ptol,
        gtol=gtol,
        diag=diag,
        epsfcn=epsfcn,
        factor=factor,
        maxfev=maxfev,
        maxiter=maxiter,
        nprint=nprint,
    )


class NlsLmControl(dict):
    """Named list with the nine ``nls.lm.control`` components, in that order."""

    def __repr__(self):
        blocks = [f"${name}\n{_show(value)}" for name, value in self.items()]
        return "\n\n".join(blocks) + "\n"


def _show(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "[1] TRUE" if value else "[1] FALSE"
    if isinstance(value, list):
        if len(value) == 0:
            return "list()"
        return "\n".join(f"[[{index}]]\n{_show(item)}" for index, item in enumerate(value, start=1))
    if isinstance(value, np.ndarray):
        if value.size == 0 and np.issubdtype(value.dtype, np.integer):
            return "integer(0)"
        if value.size == 0 and np.issubdtype(value.dtype, np.floating):
            return "numeric(0)"
        shown = " ".join(_format_scalar(item) for item in np.ravel(value))
        return f"[1] {shown}"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return f"[1] {_format_scalar(value)}"
    return str(value)


def _format_scalar(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    number = float(value)
    if number == 0.0:
        return "0"
    return format(number, ".7g")
