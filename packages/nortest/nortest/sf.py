"""Shapiro-Francia normality test."""

import math

from nortest._stats import HTest, complete, cor, data_name, pnorm, ppoints, qnorm


def sf_test(x):
    """Shapiro-Francia test of the composite hypothesis of normality.

    ``x`` must have between 5 and 5000 non-missing values. The statistic
    is the squared correlation of the ordered sample with
    ``qnorm(ppoints(n, a=3/8))``. The p-value is Royston's approximation.
    """
    label = data_name()
    values = sorted(complete(x))
    n = len(values)
    if n < 5 or n > 5000:
        raise ValueError("sample size must be between 5 and 5000")
    expected = [qnorm(point) for point in ppoints(n, a=3 / 8)]
    statistic = cor(values, expected) ** 2
    if math.isnan(statistic):
        p_value = math.nan
    else:
        u = math.log(n)
        v = math.log(u)
        mu = -1.2725 + 1.0521 * (v - u)
        sig = 1.0308 - 0.26758 * (v + 2 / u)
        z = (math.log(1 - statistic) - mu) / sig
        p_value = pnorm(z, lower_tail=False)
    return HTest(
        "W",
        statistic,
        p_value,
        "Shapiro-Francia normality test",
        label,
    )
