"""Pearson chi-square normality test."""

import math

from nortest._stats import HTest, complete, data_name, mean, pchisq, pnorm, sd, tabulate


def pearson_test(x, n_classes=None, adjust=True):
    """Pearson chi-square test of the composite hypothesis of normality.

    The default number of classes is ``ceiling(2 * n^(2/5))``, using the
    count of non-missing values. ``adjust=True`` uses ``n_classes - 3``
    degrees of freedom. ``adjust=False`` uses ``n_classes - 1``. A
    non-positive degrees of freedom warns and returns a missing p-value.
    """
    label = data_name()
    values = complete(x)
    n = len(values)
    if n_classes is None:
        n_classes = math.ceil(2 * (n ** (2 / 5)))
    dfd = 2 if adjust else 0
    center = mean(values)
    scale = sd(values)
    bins = [math.floor(1 + n_classes * pnorm(value, center, scale)) for value in values]
    counts = tabulate(bins, n_classes)
    expected = n / n_classes
    statistic = sum((count - expected) ** 2 / expected for count in counts)
    p_value = pchisq(statistic, n_classes - dfd - 1, lower_tail=False)
    return HTest(
        "P",
        statistic,
        p_value,
        "Pearson chi-square normality test",
        label,
        n_classes=n_classes,
        df=n_classes - 1 - dfd,
    )
