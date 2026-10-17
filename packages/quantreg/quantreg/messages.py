"""Small constructors that do not call the sparse or survival code."""

from __future__ import annotations

import numpy as np


_SFN = (
    "insufficient storage (work space) when calling extract\n",
    "nnzd > nnzdmax\n",
    "insufficient storage in iwork when calling ordmmd\n",
    "insufficient storage in iwork when calling sfinit\n",
    "nnzl > nnzlmax when calling sfinit\n",
    "nsub > nsubmax when calling sfinit\n",
    "insufficient work space in iwork when calling symfct\n",
    "inconsistancy in input when calling symfct\n",
    "tmpsiz > tmpmax when calling bfinit; increase tmpmax\n",
    "nonpositive diagonal encountered blkfct() matrix is not positive definite\n",
    "insufficient work storage in tmpvec when calling blkfct\n",
    "insufficient work storage in iwork  when calling blkfct\n",
    "impossible error condition",
    "impossible error condition",
    "impossible error condition",
    "impossible error condition",
    "tiny diagonals replaced with Inf when calling blkfct\n",
)


def sfn_message(ierr):
    """The storage message for an sfn Fortran error code. Codes are 1-based."""
    code = int(ierr)
    if code < 1 or code > len(_SFN):
        return None
    return _SFN[code - 1]


def sfn_control(
    nsubmax=None,
    tmpmax=None,
    nnzlmax=None,
    cachsz=64,
    small=1e-6,
    maxiter=100,
    tiny=1e-30,
    large=1e128,
    warn_mesg=True,
):
    """Storage limits for the sparse Frisch-Newton fit."""
    return {
        "nsubmax": nsubmax,
        "tmpmax": tmpmax,
        "nnzlmax": nnzlmax,
        "cachsz": cachsz,
        "small": small,
        "maxiter": int(maxiter),
        "tiny": tiny,
        "Large": large,
        "warn.mesg": warn_mesg,
    }


def nlrq_control(maxiter=100, k=2, initial_step_size=1, big=1e20, eps=1.0e-7, beta=0.97):
    """Iteration controls for nonlinear quantile regression."""
    return {
        "maxiter": maxiter,
        "k": k,
        "InitialStepSize": initial_step_size,
        "big": big,
        "eps": eps,
        "beta": beta,
    }


def curv(y, yc, ctype="left"):
    """Pair event times with censoring times. The default is the first match.arg choice, left."""
    response = np.asarray(y, dtype=float).reshape(-1)
    censor = np.asarray(yc, dtype=float).reshape(-1)
    if response.shape[0] != censor.shape[0]:
        raise ValueError("Event times and censoring times of different length")
    choice = _match_arg(ctype, ("left", "right"))
    if choice == "right" and np.any(response > censor):
        raise ValueError("Event times can not exceed ctimes for right censoring")
    if choice == "left" and np.any(response < censor):
        raise ValueError("Event times can not be less than ctimes for left censoring")
    return {
        "time": response,
        "ctime": censor,
        "ctype": choice,
        "type": choice,
        "class": "Surv",
    }


def _match_arg(value, choices):
    text = str(value)
    hits = [choice for choice in choices if choice.startswith(text)]
    if len(hits) != 1:
        raise ValueError(f"'{text}' does not match one of {choices}")
    return hits[0]
