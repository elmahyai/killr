"""Anderson-Darling normality test."""

import math

from nortest._stats import HTest, complete, data_name, mean, pnorm, zscores


def ad_test(x):
    """Anderson-Darling test of the composite hypothesis of normality.

    ``x`` must have more than 7 non-missing values. The statistic is
    ``A = -n - mean(h)`` with ``h`` the weighted sum of log normal cdfs,
    and the p-value is Stephens' table for the adjusted statistic.
    """
    label = data_name()
    values = sorted(complete(x))
    n = len(values)
    if n < 8:
        raise ValueError("sample size must be greater than 7")
    z = zscores(values)
    logp1 = [pnorm(value, log_p=True) for value in z]
    logp2 = [pnorm(-value, log_p=True) for value in z]
    weights = [(2 * i - 1) * (logp1[i - 1] + logp2[n - i]) for i in range(1, n + 1)]
    statistic = -n - mean(weights)
    adjusted = (1 + 0.75 / n + 2.25 / n**2) * statistic
    if math.isnan(adjusted):
        raise ValueError("missing value where TRUE/FALSE needed")
    if adjusted < 0.2:
        p_value = 1 - math.exp(-13.436 + 101.14 * adjusted - 223.73 * adjusted**2)
    elif adjusted < 0.34:
        p_value = 1 - math.exp(-8.318 + 42.796 * adjusted - 59.938 * adjusted**2)
    elif adjusted < 0.6:
        p_value = math.exp(0.9177 - 4.279 * adjusted - 1.38 * adjusted**2)
    elif adjusted < 10:
        p_value = math.exp(1.2937 - 5.709 * adjusted + 0.0186 * adjusted**2)
    else:
        p_value = 3.7e-24
    return HTest(
        "A",
        statistic,
        p_value,
        "Anderson-Darling normality test",
        label,
    )
