"""`mi.inference` of mix 1.0-13 (R/mix.R): Rubin's rules for multiple imputation.

The combination is array arithmetic. The t quantile and the t tail are SciPy's Student
t distribution, which is the native library for those tails in `native.json`.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def mi_inference(est, std_err, confidence: float = 0.95) -> dict:
    qstar = np.column_stack([np.ravel(np.asarray(e, dtype=float)) for e in est])
    qbar = qstar.mean(axis=1)
    u = np.column_stack([np.ravel(np.asarray(e, dtype=float)) for e in std_err]) ** 2
    ubar = u.mean(axis=1)
    bm = np.var(qstar, axis=1, ddof=1)
    m = qstar.shape[1]
    tm = ubar + (1 + 1 / m) * bm
    rem = (1 + 1 / m) * bm / ubar
    nu = (m - 1) * (1 + 1 / rem) ** 2
    alpha = 1 - (1 - confidence) / 2
    low = qbar - stats.t.ppf(alpha, nu) * np.sqrt(tm)
    up = qbar + stats.t.ppf(alpha, nu) * np.sqrt(tm)
    pval = 2 * (1 - stats.t.cdf(np.abs(qbar / np.sqrt(tm)), nu))
    fminf = (rem + 2 / (nu + 3)) / (rem + 1)
    return {"est": qbar, "std.err": np.sqrt(tm), "df": nu, "signif": pval,
            "lower": low, "upper": up, "r": rem, "fminf": fminf}
