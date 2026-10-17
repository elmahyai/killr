"""Fold-change to log-ratio from gtools 3.9.5.

``1 / -foldchange`` when foldchange is negative, otherwise foldchange, then
``log`` with exponential ``base``, with R recycling and array rules.
"""

from __future__ import annotations

import numpy as np

from gtools.foldchange import _ifelse, _unary_minus
from gtools.logit import (
    _Atom,
    _ONE,
    _binary,
    _divide,
    _logarithm,
    _materialize,
    _prepare,
)
from gtools.logratio2foldchange import _less_than

_ZERO = _Atom(np.array([0.0]), None, "double")


def foldchange2logratio(foldchange, base=2):
    """Log-ratio from fold-change values with logarithm base ``base``."""
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        values = _prepare(foldchange)
        bases = _prepare(base)
        negative = _binary(values, _ZERO, _less_than)
        reciprocal = _binary(_ONE, _unary_minus(values), _divide)
        magnitude = _ifelse(negative, reciprocal, values)
        logged = _logarithm(magnitude)
        log_base = _logarithm(bases)
        return _materialize(_binary(logged, log_base, _divide))
