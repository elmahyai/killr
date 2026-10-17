"""Lilliefors Kolmogorov-Smirnov normality test."""

import math

from nortest._stats import HTest, complete, data_name, pnorm, zscores


def lillie_test(x):
    """Lilliefors test of the composite hypothesis of normality.

    ``x`` must have more than 4 non-missing values. The p-value is the
    Dallal-Wilkinson approximation when that value is at most 0.1, and
    Stephens' approximation otherwise.
    """
    label = data_name()
    values = sorted(complete(x))
    n = len(values)
    if n < 5:
        raise ValueError("sample size must be greater than 4")
    p = [pnorm(value) for value in zscores(values)]
    if any(math.isnan(value) for value in p):
        raise ValueError("missing value where TRUE/FALSE needed")
    d_plus = max(i / n - p[i - 1] for i in range(1, n + 1))
    d_minus = max(p[i - 1] - (i - 1) / n for i in range(1, n + 1))
    statistic = max(d_plus, d_minus)
    if n <= 100:
        kd = statistic
        nd = n
    else:
        kd = statistic * (n / 100) ** 0.49
        nd = 100
    p_value = math.exp(
        -7.01256 * kd**2 * (nd + 2.78019)
        + 2.99587 * kd * math.sqrt(nd + 2.78019)
        - 0.122119
        + 0.974598 / math.sqrt(nd)
        + 1.67997 / nd
    )
    if p_value > 0.1:
        kk = (math.sqrt(n) - 0.01 + 0.85 / math.sqrt(n)) * statistic
        if kk <= 0.302:
            p_value = 1
        elif kk <= 0.5:
            p_value = (
                2.76773
                - 19.828315 * kk
                + 80.709644 * kk**2
                - 138.55152 * kk**3
                + 81.218052 * kk**4
            )
        elif kk <= 0.9:
            p_value = (
                -4.901232
                + 40.662806 * kk
                - 97.490286 * kk**2
                + 94.029866 * kk**3
                - 32.355711 * kk**4
            )
        elif kk <= 1.31:
            p_value = (
                6.198765
                - 19.558097 * kk
                + 23.186922 * kk**2
                - 12.234627 * kk**3
                + 2.423045 * kk**4
            )
        else:
            p_value = 0
    return HTest(
        "D",
        statistic,
        p_value,
        "Lilliefors (Kolmogorov-Smirnov) normality test",
        label,
    )
