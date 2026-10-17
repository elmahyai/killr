"""Stats helpers used by the normality tests.

pnorm is math.erf. The log-scale normal cdf, the normal quantile, and the
chi-square tail are SciPy, which matches R 4.5 inside 1e-8. log(erf) is
not used: at a standardized value of -8 it is already off by about 0.02.
"""

import inspect
import math
import warnings

_SQRT2 = math.sqrt(2.0)
_EPS = 2.220446049250313e-16


def complete(values):
    """Drop missing values the way complete.cases does for one vector."""
    kept = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError("non-numeric argument") from exc
        if math.isnan(number):
            continue
        kept.append(number)
    return kept


def mean(values):
    return sum(values) / len(values)


def sd(values):
    count = len(values)
    if count < 2:
        return math.nan
    center = mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (count - 1))


def cor(left, right):
    """Pearson correlation. A zero standard deviation warns and returns NaN."""
    center_left = mean(left)
    center_right = mean(right)
    dx = [value - center_left for value in left]
    dy = [value - center_right for value in right]
    sxx = sum(value * value for value in dx)
    syy = sum(value * value for value in dy)
    if sxx == 0.0 or syy == 0.0:
        warnings.warn("the standard deviation is zero", RuntimeWarning, stacklevel=3)
        return math.nan
    return sum(a * b for a, b in zip(dx, dy)) / math.sqrt(sxx * syy)


def ppoints(n, a=None):
    """R ppoints. The default a is 3/8 when n <= 10 and 1/2 otherwise."""
    if n > 1 and not isinstance(n, (int, float)):
        n = len(n)
    n = int(n)
    if a is None:
        a = 3.0 / 8.0 if n <= 10 else 0.5
    if n <= 0:
        return []
    return [(i - a) / (n + 1 - 2 * a) for i in range(1, n + 1)]


def pnorm(x, mean=0.0, sd=1.0, lower_tail=True, log_p=False):
    """R pnorm. The log scale uses SciPy's log_ndtr."""
    if math.isnan(x) or math.isnan(mean) or (isinstance(sd, float) and math.isnan(sd)):
        return math.nan
    if sd < 0 or not math.isfinite(sd):
        return math.nan
    if sd == 0:
        probability = 1.0 if x >= mean else 0.0
    else:
        z = (x - mean) / sd
        if log_p:
            from scipy.special import log_ndtr

            return float(log_ndtr(z if lower_tail else -z))
        probability = 0.5 * (1.0 + math.erf(z / _SQRT2))
    if not lower_tail:
        probability = 1.0 - probability
    if log_p:
        return math.log(probability) if probability > 0.0 else -math.inf
    return probability


def qnorm(p, mean=0.0, sd=1.0, lower_tail=True, log_p=False):
    """R qnorm via SciPy's ppf."""
    from scipy.stats import norm

    if log_p:
        p = math.exp(p)
    if not lower_tail:
        p = 1.0 - p
    if math.isnan(p) or sd < 0 or not math.isfinite(sd) or not 0.0 <= p <= 1.0:
        return math.nan
    if sd == 0:
        return mean
    return float(norm.ppf(p)) * sd + mean


def pchisq(q, df, lower_tail=True):
    """R pchisq. A non-positive df warns and returns NaN, as pchisq does."""
    from scipy.stats import chi2

    if math.isnan(q) or math.isnan(df) or df <= 0:
        warnings.warn("NaNs produced", RuntimeWarning, stacklevel=3)
        return math.nan
    if lower_tail:
        return float(chi2.cdf(q, df))
    return float(chi2.sf(q, df))


def tabulate(bins, nbins):
    """R tabulate. Non-positive values and values past nbins are ignored."""
    size = int(math.trunc(nbins))
    counts = [0] * max(size, 0)
    for value in bins:
        if math.isnan(value):
            continue
        index = int(math.trunc(value))
        if 1 <= index <= size:
            counts[index - 1] += 1
    return counts


def zscores(values):
    """(x - mean) / sd. A zero sd yields NaN, which is R's 0/0."""
    center = mean(values)
    scale = sd(values)
    if scale == 0.0 or math.isnan(scale):
        return [math.nan] * len(values)
    return [(value - center) / scale for value in values]


def data_name():
    """Deparsed first argument of the caller, when the source line is available."""
    frame = inspect.currentframe().f_back.f_back
    info = inspect.getframeinfo(frame)
    if not info.code_context:
        return "x"
    line = info.code_context[0]
    names = ("ad_test", "cvm_test", "lillie_test", "pearson_test", "sf_test")
    start = -1
    for name in names:
        mark = line.find(name + "(")
        if mark >= 0:
            start = mark + len(name) + 1
            break
    if start < 0:
        return "x"
    depth = 1
    end = start
    while end < len(line) and depth:
        if line[end] == "(":
            depth += 1
        elif line[end] == ")":
            depth -= 1
            if depth == 0:
                break
        end += 1
    argument = line[start:end].strip()
    paren = bracket = brace = 0
    quote = ""
    for index, char in enumerate(argument):
        if quote:
            if char == quote and argument[index - 1] != "\\":
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "[":
            bracket += 1
        elif char == "]":
            bracket -= 1
        elif char == "{":
            brace += 1
        elif char == "}":
            brace -= 1
        elif char == "," and paren == bracket == brace == 0:
            argument = argument[:index].strip()
            break
    return argument or "x"


def _format_number(value, digits):
    if isinstance(value, float) and math.isnan(value):
        return "NA"
    return format(float(value), f".{digits}g")


class HTest:
    """An htest list, printed the way print.htest prints it."""

    def __init__(self, name, statistic, p_value, method, data_name, **extra):
        self.statistic_name = name
        self.statistic = statistic
        self.p_value = p_value
        self.method = method
        self.data_name = data_name
        self.extra = extra

    def __iter__(self):
        yield ("statistic", self.statistic)
        yield ("p.value", self.p_value)
        yield ("method", self.method)
        yield ("data.name", self.data_name)
        yield from self.extra.items()

    def __str__(self):
        stat = _format_number(self.statistic, 5)
        if isinstance(self.p_value, float) and math.isnan(self.p_value):
            p_bit = "p-value = NA"
        elif self.p_value < _EPS:
            p_bit = "p-value < 2.2e-16"
        else:
            p_bit = "p-value = " + _format_number(self.p_value, 4)
        return (
            f"\n\t{self.method}\n\ndata:  {self.data_name}\n"
            f"{self.statistic_name} = {stat}, {p_bit}\n\n"
        )
