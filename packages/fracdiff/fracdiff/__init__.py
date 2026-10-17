"""Fractionally differenced ARIMA, translated from fracdiff 1.5-4.

The fractional difference uses NumPy's FFT. The Haslett-Raftery fit for an
ARFIMA(0, d, 0) model is the Brent search in the installed C. A positive
autoregressive or moving-average order is still that MINPACK fit.
"""

from fracdiff.fit import (
    Fracdiff,
    confint_fracdiff,
    diffseries,
    fd_gph,
    fd_sperio,
    fracdiff,
    fracdiff_sim,
    fracdiff_var,
)

__all__ = [
    "Fracdiff",
    "confint_fracdiff",
    "diffseries",
    "fd_gph",
    "fd_sperio",
    "fracdiff",
    "fracdiff_sim",
    "fracdiff_var",
]
