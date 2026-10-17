"""Einstein functions."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.special_common import is_complex_value, is_numeric_value, length_of


def einsteinF(d, x):
    if not is_numeric_value(x) and not is_complex_value(x):
        raise PracmaError("is.numeric(x) || is.complex(x) is not TRUE")
    if length_of(d) > 1:
        raise PracmaError("the condition has length > 1")
    degree = float(np.asarray(d).reshape(-1)[0])
    values = np.ravel(np.asarray(x), order="F")
    zeros = values == 0
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if degree == 1:
            y = values**2 * np.exp(values) / (np.exp(values) - 1) ** 2
            y = np.array(y, copy=True)
            y[zeros] = 1
        elif degree == 2:
            y = values / (np.exp(values) - 1)
            y = np.array(y, copy=True)
            y[zeros] = 1
        elif degree == 3:
            y = np.log(1 - np.exp(-values))
            y = np.array(y, copy=True)
            y[zeros] = -np.inf
        elif degree == 4:
            y = values / (np.exp(values) - 1) - np.log(1 - np.exp(-values))
            y = np.array(y, copy=True)
            y[zeros] = np.inf
        else:
            raise PracmaError("Argument 'd' must be one of the integers 1, 2, 3, 4.")
    return y
