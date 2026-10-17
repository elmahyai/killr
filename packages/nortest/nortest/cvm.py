"""Cramer-von Mises normality test."""

import math
import warnings

from nortest._stats import HTest, complete, data_name, pnorm, zscores


def cvm_test(x):
    """Cramer-von Mises test of the composite hypothesis of normality.

    ``x`` must have more than 7 non-missing values. When the adjusted
    statistic is at least 1.1, the p-value is reported as 7.37e-10 and a
    warning says it cannot be computed more accurately.
    """
    label = data_name()
    values = sorted(complete(x))
    n = len(values)
    if n < 8:
        raise ValueError("sample size must be greater than 7")
    p = [pnorm(value) for value in zscores(values)]
    if any(math.isnan(value) for value in p):
        raise ValueError("missing value where TRUE/FALSE needed")
    statistic = 1 / (12 * n) + sum(
        (p[i - 1] - (2 * i - 1) / (2 * n)) ** 2 for i in range(1, n + 1)
    )
    adjusted = (1 + 0.5 / n) * statistic
    if adjusted < 0.0275:
        p_value = 1 - math.exp(-13.953 + 775.5 * adjusted - 12542.61 * adjusted**2)
    elif adjusted < 0.051:
        p_value = 1 - math.exp(-5.903 + 179.546 * adjusted - 1515.29 * adjusted**2)
    elif adjusted < 0.092:
        p_value = math.exp(0.886 - 31.62 * adjusted + 10.897 * adjusted**2)
    elif adjusted < 1.1:
        p_value = math.exp(1.111 - 34.242 * adjusted + 12.832 * adjusted**2)
    else:
        warnings.warn(
            "p-value is smaller than 7.37e-10, cannot be computed more accurately",
            RuntimeWarning,
            stacklevel=2,
        )
        p_value = 7.37e-10
    return HTest(
        "W",
        statistic,
        p_value,
        "Cramer-von Mises normality test",
        label,
    )
