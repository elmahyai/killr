"""Sample moments and the normality tests from moments 0.14.1.

Vectors are lists. A Matrix is stored by column, the way R fills a matrix.
A Frame is a data frame: all.moments still returns a Matrix, while
all.cumulants and central2raw return a Frame whose columns are named X1, X2,
and so on. kappa[2] is the first central moment and kappa[3] is the second.
"""

from __future__ import annotations

import inspect
import math

_SQRT2 = math.sqrt(2.0)
_ALTERNATIVES = ("two.sided", "less", "greater")


class Matrix:
    """Numeric matrix stored by column. colnames are kept when they are set."""

    def __init__(self, columns, colnames=None):
        columns = [list(column) for column in columns]
        if not columns:
            raise ValueError("matrix has no columns")
        nrow = len(columns[0])
        for column in columns:
            if len(column) != nrow:
                raise ValueError("columns differ in length")
        self.columns = columns
        if colnames is None:
            self.colnames = None
        else:
            self.colnames = [str(name) for name in colnames]
            if len(self.colnames) != len(columns):
                raise ValueError("colnames do not match the columns")

    def __repr__(self):
        body = ", ".join(repr(column) for column in self.columns)
        return f"Matrix([{body}])"

    def __str__(self):
        return _format_columns(self.columns, self.colnames)


class Frame:
    """Data frame stored by column. Missing names become X1, X2, and so on."""

    def __init__(self, columns, colnames=None):
        columns = [list(column) for column in columns]
        if not columns:
            raise ValueError("data frame has no columns")
        nrow = len(columns[0])
        for column in columns:
            if len(column) != nrow:
                raise ValueError("columns differ in length")
        if colnames is None:
            colnames = [f"X{index + 1}" for index in range(len(columns))]
        self.colnames = [str(name) for name in colnames]
        if len(self.colnames) != len(columns):
            raise ValueError("colnames do not match the columns")
        self.columns = columns

    def __repr__(self):
        body = ", ".join(repr(column) for column in self.columns)
        return f"Frame([{body}], {self.colnames!r})"

    def __str__(self):
        return _format_columns(self.columns, self.colnames)


class Named:
    """A numeric vector with names, as apply and sapply return them."""

    def __init__(self, values, names):
        self.values = list(values)
        self.names = [str(name) for name in names]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]

    def __repr__(self):
        return f"Named({self.values!r}, {self.names!r})"

    def __str__(self):
        return _format_row(self.values, self.names)


class HTest:
    """The htest list the four tests return."""

    def __init__(self, statistic, p_value, alternative, method, data_name):
        self.statistic = dict(statistic)
        self.p_value = p_value
        self.alternative = alternative
        self.method = method
        self.data_name = data_name

    def __repr__(self):
        return (
            f"HTest({self.statistic!r}, p_value={self.p_value!r}, "
            f"alternative={self.alternative!r}, method={self.method!r}, "
            f"data_name={self.data_name!r})"
        )

    def __str__(self):
        pieces = [f"{name} = {_format_stat(value)}" for name, value in self.statistic.items()]
        pieces.append(f"p-value = {_format_stat(self.p_value)}")
        return (
            f"\n\t{self.method}\n\n"
            f"data:  {self.data_name}\n"
            f"{', '.join(pieces)}\n"
            f"alternative hypothesis: {self.alternative}\n"
        )


def moment(x, order=1, central=False, absolute=False, na_rm=False):
    """Sample moment. A matrix or data frame is reduced one column at a time."""
    central = _flag(central)
    absolute = _flag(absolute)
    na_rm = _flag(na_rm)
    kind, columns, names = _columns(x)
    values = [_moment_vector(column, order, central, absolute, na_rm) for column in columns]
    if kind == "vector":
        return values[0]
    if names:
        return Named(values, names)
    return values


def all_moments(x, order_max=2, central=False, absolute=False, na_rm=False):
    """Moments of every order from 0 through order_max."""
    _check_order_max(order_max)
    central = _flag(central)
    absolute = _flag(absolute)
    na_rm = _flag(na_rm)
    kind, columns, _names = _columns(x)
    orders = range(0, math.trunc(float(order_max)) + 1)
    if kind == "vector":
        return [_moment_vector(columns[0], order, central, absolute, na_rm) for order in orders]
    out = []
    for column in columns:
        out.append([_moment_vector(column, order, central, absolute, na_rm) for order in orders])
    return Matrix(out)


def raw2central(mu_raw):
    """Binomial conversion from raw moments to central moments."""
    if isinstance(mu_raw, Matrix):
        columns = [_raw_to_central(column) for column in mu_raw.columns]
        return Matrix(columns, mu_raw.colnames)
    if isinstance(mu_raw, Frame):
        columns = [_raw_to_central(column) for column in mu_raw.columns]
        return Matrix(columns, mu_raw.colnames)
    if isinstance(mu_raw, Named):
        return _raw_to_central(mu_raw.values)
    if _is_vector(mu_raw):
        return _raw_to_central(_as_vector(mu_raw))
    if isinstance(mu_raw, (int, float)) and not isinstance(mu_raw, bool):
        return _raw_to_central([float(mu_raw)])
    raise TypeError("argument mu.raw is not a vector, matrix or data frame")


def central2raw(mu_central, eta):
    """Binomial conversion from central moments back to raw moments."""
    means = _as_eta(eta)
    if isinstance(mu_central, Named):
        mu_central = mu_central.values
    if _is_vector(mu_central):
        if len(means) > 1:
            raise ValueError("argument eta has too many values")
        return _central_to_raw(_as_vector(mu_central), means[0])
    if isinstance(mu_central, (Matrix, Frame)):
        if len(means) != len(mu_central.columns):
            raise ValueError("argument eta does not match the argument mu.central")
        columns = [
            _central_to_raw(column, mean)
            for column, mean in zip(mu_central.columns, means)
        ]
        if isinstance(mu_central, Frame):
            return Frame(columns)
        return Matrix(columns)
    raise ValueError("argument mu.central is not a vector, matrix or data frame")


def all_cumulants(mu_raw):
    """Cumulants from a vector, matrix, or data frame of raw moments."""
    central = raw2central(mu_raw)
    if isinstance(mu_raw, Matrix):
        columns = [
            _cumulants(raw, cent)
            for raw, cent in zip(mu_raw.columns, central.columns)
        ]
        return Matrix(columns)
    if isinstance(mu_raw, Frame):
        columns = [
            _cumulants(raw, cent)
            for raw, cent in zip(mu_raw.columns, central.columns)
        ]
        return Frame(columns)
    if isinstance(mu_raw, Named) or _is_vector(mu_raw) or (
        isinstance(mu_raw, (int, float)) and not isinstance(mu_raw, bool)
    ):
        raw = mu_raw.values if isinstance(mu_raw, Named) else _as_vector(mu_raw)
        return _cumulants(raw, central)
    raise ValueError("argument mu.raw is not a vector, matrix or data frame")


def skewness(x, na_rm=False):
    """The moment skewness, g1 with the population second moment."""
    return _column_stat(x, na_rm, _skewness_vector)


def kurtosis(x, na_rm=False):
    """Pearson's kurtosis. A normal sample is near 3."""
    return _column_stat(x, na_rm, _kurtosis_vector)


def geary(x, na_rm=False):
    """Geary's kurtosis, the mean absolute deviation over the root mean square."""
    return _column_stat(x, na_rm, _geary_vector)


def agostino_test(x, alternative="two.sided"):
    """D'Agostino skewness test. The sample size must be from 8 to 46340."""
    name = _data_name("agostino_test")
    values = _complete_vector(x)
    alter, alternative_name = _alternative(alternative)
    n = len(values)
    if n < 8 or n > 46340:
        raise ValueError("sample size must be between 8 and 46340")
    s3 = _skewness_vector(values)
    y = s3 * math.sqrt((n + 1) * (n + 3) / (6 * (n - 2)))
    b2 = (
        3
        * (n * n + 27 * n - 70)
        * (n + 1)
        * (n + 3)
        / ((n - 2) * (n + 5) * (n + 7) * (n + 9))
    )
    w = _sqrt(-1 + _sqrt(2 * (b2 - 1)))
    d = 1 / _sqrt(_log(w))
    a = _sqrt(2 / (w * w - 1))
    z = d * _log(y / a + _sqrt((y / a) ** 2 + 1))
    p_value, text = _sided_p(
        z,
        alter,
        "data have a skewness",
        "data have positive skewness",
        "data have negative skewness",
    )
    return HTest({"skew": s3, "z": z}, p_value, text, "D'Agostino skewness test", name)


def anscombe_test(x, alternative="two.sided"):
    """Anscombe-Glynn kurtosis test. The null kurtosis is 3."""
    name = _data_name("anscombe_test")
    values = _complete_vector(x)
    alter, _alternative_name = _alternative(alternative)
    n = len(values)
    b = _kurtosis_vector(values)
    eb2 = 3 * (n - 1) / (n + 1)
    vb2 = 24 * n * (n - 2) * (n - 3) / ((n + 1) ** 2 * (n + 3) * (n + 5))
    m3 = (6 * (n**2 - 5 * n + 2) / ((n + 7) * (n + 9))) * _sqrt(
        (6 * (n + 3) * (n + 5)) / (n * (n - 2) * (n - 3))
    )
    a = 6 + (8 / m3) * (2 / m3 + _sqrt(1 + 4 / _r_pow(m3, 2)))
    xx = (b - eb2) / _sqrt(vb2)
    inside = (1 - 2 / a) / (1 + xx * _sqrt(2 / (a - 4)))
    z = (1 - 2 / (9 * a) - _r_pow(inside, 1 / 3)) / _sqrt(2 / (9 * a))
    p_value, text = _sided_p(
        z,
        alter,
        "kurtosis is not equal to 3",
        "kurtosis is greater than 3",
        "kurtosis is lower than 3",
    )
    return HTest({"kurt": b, "z": z}, p_value, text, "Anscombe-Glynn kurtosis test", name)


def bonett_test(x, alternative="two.sided"):
    """Bonett-Seier test of Geary's kurtosis. The null value is sqrt(2/pi)."""
    name = _data_name("bonett_test")
    values = _complete_vector(x)
    alter, _alternative_name = _alternative(alternative)
    n = len(values)
    center = _mean(values)
    deviations = [_sub(value, center) for value in values]
    rho = _sqrt(_div(_sum(_square(value) for value in deviations), n))
    tau = _div(_sum(_abs(value) for value in deviations), n)
    omega = 13.29 * (_log(rho) - _log(tau))
    z = _sqrt(n + 2) * (omega - 3) / 3.54
    p_value, text = _sided_p(
        z,
        alter,
        "kurtosis is not equal to sqrt(2/pi)",
        "kurtosis is greater than sqrt(2/pi)",
        "kurtosis is lower than sqrt(2/pi)",
    )
    return HTest(
        {"tau": tau, "z": z},
        p_value,
        text,
        "Bonett-Seier test for Geary kurtosis",
        name,
    )


def jarque_test(x):
    """Jarque-Bera test. The statistic is chi-square with two degrees of freedom."""
    name = _data_name("jarque_test")
    if isinstance(x, (Matrix, Frame)):
        raise ValueError("argument x is not a vector")
    if not _is_vector(x) and not (isinstance(x, (int, float)) and not isinstance(x, bool)):
        raise ValueError("argument x is not a vector")
    values = _as_vector(x)
    if not _is_numeric(values):
        raise ValueError("argument x is not numeric")
    numbers = [_number(value) for value in values]
    n = len(numbers)
    kurt = _kurtosis_vector(numbers)
    skew = _skewness_vector(numbers)
    jb = _mul(n / 6, _add(_square(skew), _mul(0.25, _square(_sub(kurt, 3)))))
    return HTest(
        {"JB": jb},
        _pchisq_upper(jb, 2),
        "greater",
        "Jarque-Bera Normality Test",
        name,
    )


def _moment_vector(values, order, central, absolute, na_rm):
    numbers = [_number(value) for value in values]
    if na_rm:
        numbers = [value for value in numbers if value is not None and not _is_nan(value)]
    if central:
        numbers = [_sub(value, _mean(numbers)) for value in numbers]
    if absolute:
        numbers = [_abs(value) for value in numbers]
    total = _sum(_r_pow(value, order) for value in numbers)
    return _div(total, len(numbers))


def _skewness_vector(values):
    n = len(values)
    center = _mean(values)
    deviations = [_sub(value, center) for value in values]
    second = _div(_sum(_r_pow(value, 2) for value in deviations), n)
    third = _div(_sum(_r_pow(value, 3) for value in deviations), n)
    return _div(third, _r_pow(second, 1.5))


def _kurtosis_vector(values):
    n = len(values)
    center = _mean(values)
    deviations = [_sub(value, center) for value in values]
    numerator = _mul(n, _sum(_r_pow(value, 4) for value in deviations))
    denominator = _r_pow(_sum(_r_pow(value, 2) for value in deviations), 2)
    return _div(numerator, denominator)


def _geary_vector(values):
    n = len(values)
    center = _mean(values)
    deviations = [_sub(value, center) for value in values]
    rho = _sqrt(_div(_sum(_r_pow(value, 2) for value in deviations), n))
    tau = _div(_sum(_abs(value) for value in deviations), n)
    return _div(tau, rho)


def _column_stat(x, na_rm, function):
    na_rm = _flag(na_rm)
    kind, columns, names = _columns(x)
    values = []
    for column in columns:
        numbers = [_number(value) for value in column]
        if na_rm:
            numbers = [value for value in numbers if value is not None and not _is_nan(value)]
        values.append(function(numbers))
    if kind == "vector":
        return values[0]
    if names:
        return Named(values, names)
    return values


def _raw_to_central(mu_raw):
    mu = [_number(value) for value in mu_raw]
    if len(mu) < 2:
        raise IndexError("subscript out of bounds")
    n = len(mu) - 1
    central = [0.0] * len(mu)
    central[0] = 1.0
    eta = mu[1]
    for k in range(1, n + 1):
        total = 0.0
        for i in range(0, k + 1):
            term = _mul(_choose(k, i), _r_pow(_neg(eta), k - i))
            total = _add(total, _mul(term, mu[i]))
        central[k] = total
    return central


def _central_to_raw(mu_central, eta):
    mu = [_number(value) for value in mu_central]
    eta = _number(eta)
    n = len(mu) - 1
    raw = [0.0] * len(mu)
    if not mu:
        return raw
    raw[0] = 1.0
    for k in range(1, n + 1):
        total = 0.0
        for i in range(0, k + 1):
            term = _mul(_choose(k, i), _r_pow(eta, k - i))
            total = _add(total, _mul(term, mu[i]))
        raw[k] = total
    return raw


def _cumulants(mu_raw, mu_central):
    order_max = len(mu_raw) - 1
    if order_max < 2:
        raise IndexError("subscript out of bounds")
    kappa = [0.0] * (order_max + 1)
    kappa[1] = mu_central[1]
    kappa[2] = mu_central[2]
    for n in range(3, order_max + 1):
        total = mu_raw[n]
        for k in range(1, n):
            term = _mul(_choose(n - 1, k - 1), kappa[k])
            total = _sub(total, _mul(term, mu_raw[n - k]))
        kappa[n] = total
    return kappa


def _sided_p(z, alter, two_sided, less, greater):
    p_value = _pnorm_sf(z)
    if alter == 0:
        p_value = _mul(2, p_value)
        if p_value is None or _is_nan(p_value):
            raise ValueError("missing value where TRUE/FALSE needed")
        if p_value > 1:
            p_value = 2 - p_value
        return p_value, two_sided
    if alter == 1:
        return p_value, less
    return _sub(1, p_value), greater


def _pnorm_sf(z):
    """Upper tail of the standard normal. NA stays NA and NaN stays NaN."""
    if z is None:
        return None
    if _is_nan(z):
        return float("nan")
    if math.isinf(z):
        return 0.0 if z > 0 else 1.0
    return 0.5 * math.erfc(z / _SQRT2)


def _pchisq_upper(q, df):
    """1 - pchisq(q, df). SciPy's cdf matches that subtraction inside 1e-8."""
    if q is None:
        return None
    if _is_nan(q):
        return float("nan")
    from scipy.stats import chi2

    return 1.0 - float(chi2.cdf(q, df))


def _complete_vector(x):
    if isinstance(x, (Matrix, Frame)):
        raise ValueError("argument x is not a vector")
    values = _as_vector(x)
    if not _is_numeric(values):
        raise ValueError("argument x is not numeric")
    kept = []
    for value in values:
        number = _number(value)
        if number is None or _is_nan(number):
            continue
        kept.append(number)
    return kept


def _alternative(alternative):
    if alternative is None:
        return 0, "two.sided"
    if not isinstance(alternative, str):
        raise TypeError("alternative is not a character string")
    hits = [choice for choice in _ALTERNATIVES if choice.startswith(alternative)]
    if len(hits) != 1:
        listed = ", ".join(f"“{choice}”" for choice in _ALTERNATIVES)
        raise ValueError(f"'arg' should be one of {listed}")
    name = hits[0]
    return _ALTERNATIVES.index(name), name


def _data_name(function_name):
    frame = inspect.currentframe()
    try:
        caller = frame.f_back.f_back
        info = inspect.getframeinfo(caller)
        if not info.code_context:
            return "x"
        line = " ".join(part.strip() for part in info.code_context)
        token = function_name + "("
        start = line.find(token)
        if start < 0:
            return "x"
        start += len(token)
        depth = 1
        end = start
        while end < len(line) and depth:
            if line[end] == "(":
                depth += 1
            elif line[end] == ")":
                depth -= 1
            if depth:
                end += 1
        argument = line[start:end].split(",")[0].strip()
        return argument or "x"
    finally:
        del frame


def _columns(x):
    if isinstance(x, Matrix):
        return "matrix", x.columns, x.colnames
    if isinstance(x, Frame):
        return "frame", x.columns, x.colnames
    return "vector", [_as_vector(x)], None


def _is_vector(x):
    return isinstance(x, (list, tuple)) and not isinstance(x, (str, bytes))


def _as_vector(x):
    if _is_vector(x):
        return list(x)
    if isinstance(x, Named):
        return list(x.values)
    if isinstance(x, bool) or x is None:
        return [x]
    if isinstance(x, (int, float)):
        return [x]
    raise TypeError("argument x is not a vector")


def _as_eta(eta):
    if isinstance(eta, Named):
        return [_number(value) for value in eta.values]
    if _is_vector(eta):
        return [_number(value) for value in eta]
    if isinstance(eta, (int, float)) and not isinstance(eta, bool):
        return [float(eta)]
    if eta is None:
        return [None]
    raise TypeError("argument eta is not numeric")


def _is_numeric(values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
    return True


def _number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        number = float(value)
        if number == 0.0:
            return 0.0
        return number
    raise TypeError("non-numeric argument")


def _flag(value):
    if _is_vector(value):
        if len(value) != 1:
            raise ValueError("the condition has length > 1")
        value = value[0]
    if value is None or _is_nan(value):
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(value, bool):
        return value
    if value == 0:
        return False
    if value == 1:
        return True
    raise ValueError("the condition has length > 1")


def _check_order_max(order_max):
    if order_max is None or _is_nan(order_max):
        raise ValueError("missing value where TRUE/FALSE needed")
    if order_max < 2:
        raise ValueError("maximum order should be at least 2")


def _is_nan(value):
    return isinstance(value, float) and math.isnan(value)


def _add(left, right):
    if left is None or right is None:
        return None
    if _is_nan(left) or _is_nan(right):
        return float("nan")
    return left + right


def _sub(left, right):
    if left is None or right is None:
        return None
    if _is_nan(left) or _is_nan(right):
        return float("nan")
    return left - right


def _mul(left, right):
    if left is None or right is None:
        return None
    if _is_nan(left) or _is_nan(right):
        return float("nan")
    return left * right


def _div(left, right):
    if left is None or right is None:
        return None
    if _is_nan(left) or _is_nan(right):
        return float("nan")
    if right == 0:
        if left == 0:
            return float("nan")
        return math.copysign(math.inf, left)
    return left / right


def _neg(value):
    if value is None:
        return None
    if _is_nan(value):
        return float("nan")
    return -value


def _abs(value):
    if value is None:
        return None
    if _is_nan(value):
        return float("nan")
    return abs(value)


def _square(value):
    return _r_pow(value, 2)


def _sqrt(value):
    if value is None:
        return None
    if _is_nan(value) or value < 0:
        return float("nan")
    return math.sqrt(value)


def _log(value):
    if value is None:
        return None
    if _is_nan(value) or value < 0:
        return float("nan")
    if value == 0:
        return float("-inf")
    return math.log(value)


def _sum(values):
    total = 0.0
    seen_nan = False
    for value in values:
        if value is None:
            return None
        if _is_nan(value):
            seen_nan = True
            continue
        total += value
    if seen_nan:
        return float("nan")
    return total


def _mean(values):
    return _div(_sum(values), len(values))


def _choose(n, k):
    if k < 0 or k > n:
        return 0.0
    return float(math.comb(n, k))


def _r_pow(base, order):
    """Real power. An order of 0 is 1, including NA^0. A negative base to a non-integer is NaN."""
    if order is None or _is_nan(order):
        return None if order is None else float("nan")
    if order == 0:
        return 1.0
    if base is None:
        return None
    if _is_nan(base):
        return float("nan")
    if base < 0 and not _integer_valued(order):
        return float("nan")
    try:
        result = base ** order
    except OverflowError:
        return math.copysign(math.inf, base) if order > 0 else 0.0
    if isinstance(result, complex):
        return float("nan")
    return float(result)


def _integer_valued(order):
    return isinstance(order, (int, float)) and float(order).is_integer()


def _format_stat(value):
    if value is None:
        return "NA"
    if _is_nan(value):
        return "NaN"
    if isinstance(value, float) and math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return f"{value:.5g}"


def _format_row(values, names):
    cells = [_format_stat(value) for value in values]
    if not names:
        return " ".join(cells)
    width = max(len(name) for name in names)
    width = max(width, max(len(cell) for cell in cells))
    head = " ".join(name.rjust(width) for name in names)
    body = " ".join(cell.rjust(width) for cell in cells)
    return f"{head}\n{body}"


def _format_columns(columns, colnames):
    if not columns:
        return ""
    rows = list(zip(*columns))
    rendered = [[_format_stat(value) for value in row] for row in rows]
    width = 1
    for row in rendered:
        width = max(width, max(len(cell) for cell in row))
    if colnames:
        width = max(width, max(len(name) for name in colnames))
        lines = [" ".join(name.rjust(width) for name in colnames)]
    else:
        lines = []
    for index, row in enumerate(rendered, start=1):
        prefix = f"[{index},]"
        lines.append(prefix + " " + " ".join(cell.rjust(width) for cell in row))
    return "\n".join(lines)
