"""Univariate polynomials, matching polynom 1.4-1.

Coefficients are stored lowest degree first, and a trailing zero is dropped.
Arithmetic follows the R methods. Roots are the eigenvalues of the companion
matrix. Orthogonal polynomials use the same QR recurrence as stats::poly.
"""

from __future__ import annotations

import math

import numpy as np

_TOL = math.sqrt(np.finfo(float).eps)


def r_character_double(value: float) -> str:
    """Match R's as.character for a double."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def _coefs(values):
    if values is None:
        return [0.0]
    if isinstance(values, Polynomial):
        return list(values.coef)
    if isinstance(values, (int, float)) and not isinstance(values, bool):
        return [float(values)]
    coef = [float(item) for item in values]
    return coef or [0.0]


def _trim(coef):
    coef = [float(item) for item in coef]
    while len(coef) > 1 and coef[-1] == 0.0:
        coef.pop()
    return coef or [0.0]


class Polynomial:
    def __init__(self, coef=(0, 1)):
        self.coef = _trim(_coefs(coef))

    def __repr__(self):
        return as_character(self)

    def __len__(self):
        return len(self.coef)

    def __iter__(self):
        return iter(self.coef)

    def __eq__(self, other):
        if not isinstance(other, Polynomial):
            other = polynomial(other)
        return self.coef == other.coef

    def __ne__(self, other):
        return not self == other

    def __pos__(self):
        return polynomial(self.coef)

    def __neg__(self):
        return polynomial([-item for item in self.coef])

    def __add__(self, other):
        other = polynomial(other)
        width = max(len(self), len(other))
        left = self.coef + [0.0] * (width - len(self))
        right = other.coef + [0.0] * (width - len(other))
        return polynomial([a + b for a, b in zip(left, right)])

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-polynomial(other))

    def __rsub__(self, other):
        return polynomial(other) - self

    def __mul__(self, other):
        other = polynomial(other)
        if len(self) == 1:
            return polynomial([self.coef[0] * item for item in other.coef])
        if len(other) == 1:
            return polynomial([other.coef[0] * item for item in self.coef])
        acc = {}
        for i, a in enumerate(self.coef):
            for j, b in enumerate(other.coef):
                acc[i + j] = acc.get(i + j, 0.0) + a * b
        return polynomial([acc[k] for k in range(max(acc) + 1)])

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        other = polynomial(other)
        if len(other.coef) == 0:
            raise RuntimeError("unsupported polynomial division")
        if len(other) == 1:
            scale = other.coef[0]
            return polynomial([item / scale for item in self.coef])
        return polynomial(_divmod(self.coef, other.coef)[0])

    def __rtruediv__(self, other):
        return polynomial(other) / self

    def __mod__(self, other):
        other = polynomial(other)
        if len(other) == 1:
            return polynomial(0)
        return polynomial(_divmod(self.coef, other.coef)[1])

    def __pow__(self, power):
        if isinstance(power, Polynomial):
            if len(power) != 1:
                raise RuntimeError("unsupported polynomial power")
            power = power.coef[0]
        if power < 0 or power % 1 != 0:
            raise RuntimeError("unsupported polynomial power")
        power = int(power)
        if power == 0:
            return polynomial(1)
        if power == 1:
            return polynomial(self.coef)
        result = polynomial(self.coef)
        for _ in range(1, power):
            result = result * self
        return result

    def __call__(self, newdata):
        return predict(self, newdata)


def polynomial(coef=(0, 1)):
    if isinstance(coef, Polynomial):
        return Polynomial(coef.coef)
    return Polynomial(coef)


def as_polynomial(p):
    return p if is_polynomial(p) else polynomial(p)


def is_polynomial(p):
    return isinstance(p, Polynomial)


def _divmod(dividend, divisor):
    """Quotient and remainder. Coefficients are lowest degree first."""
    p = list(reversed(dividend))
    q = list(reversed(divisor))
    width = len(divisor)
    quot = []
    while len(p) >= width:
        d = p[0] / q[0]
        quot.append(d)
        for i in range(width):
            p[i] -= d * q[i]
        p = p[1:]
    remainder = list(reversed(p)) if p else [0.0]
    quotient = list(reversed(quot)) if quot else [0.0]
    return quotient, remainder


def coef(p):
    return list(polynomial(p).coef)


def as_character(x, decreasing=False):
    p = polynomial(x)
    pairs = [(degree, value) for degree, value in enumerate(p.coef) if value != 0.0]
    if not pairs:
        return "0"
    if decreasing:
        pairs.reverse()
    signs = ["- " if value < 0 else "+ " for _, value in pairs]
    signs[0] = "-" if signs[0] == "- " else ""
    parts = []
    for (degree, value), sign in zip(pairs, signs):
        text = r_character_double(abs(value))
        if text == "1" and degree != 0:
            text = ""
        if degree == 0:
            power = ""
        elif degree == 1:
            power = "x"
        else:
            power = f"x^{degree}"
        star = "" if text == "" or power == "" else "*"
        parts.append(f"{sign}{text}{star}{power}")
    return " ".join(parts)


def deriv(expr):
    if isinstance(expr, Polylist):
        return Polylist([deriv(item) for item in expr])
    coefs = coef(expr)
    if len(coefs) == 1:
        return polynomial(0)
    tail = coefs[1:]
    return polynomial([value * (index + 1) for index, value in enumerate(tail)])


def integral(expr, limits=None):
    if isinstance(expr, Polylist):
        return Polylist([integral(item, limits) for item in expr])
    coefs = coef(expr)
    integrated = polynomial([0.0] + [value / (index + 1) for index, value in enumerate(coefs)])
    if limits is None:
        return integrated
    values = predict(integrated, limits)
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]


def predict(object, newdata):
    high = list(reversed(coef(object)))
    if isinstance(newdata, (int, float)) and not isinstance(newdata, bool):
        value = 0.0
        for term in high:
            value = newdata * value + term
        return value
    out = []
    for point in newdata:
        value = 0.0
        for term in high:
            value = point * value + term
        out.append(value)
    return out


def monic(p):
    coefs = coef(p)
    if all(item == 0.0 for item in coefs):
        return polynomial(0)
    scale = coefs[-1]
    return polynomial([item / scale for item in coefs])


def _companion_roots(coefs):
    coefs = list(coefs)
    roots = []
    if coefs and coefs[0] == 0.0:
        zeros = 0
        while zeros < len(coefs) and coefs[zeros] == 0.0:
            zeros += 1
        coefs = coefs[zeros:]
        roots = [0.0] * zeros
    if len(coefs) <= 1:
        return roots
    if len(coefs) == 2:
        return sorted(roots + [-coefs[0] / coefs[1]])
    high = list(reversed(coefs))
    scale = high[0]
    reduced = [item / scale for item in high[1:]]
    size = len(reduced)
    matrix = np.zeros((size, size))
    matrix[0, :] = [-item for item in reduced]
    if size > 1:
        matrix[1:, :-1] = np.eye(size - 1)
    values = np.linalg.eigvals(matrix)
    cleaned = []
    for value in values:
        number = complex(value)
        if abs(number.imag) <= 1e-10:
            cleaned.append(float(number.real))
        else:
            cleaned.append(number)
    cleaned.sort(key=lambda item: (item.real, item.imag) if isinstance(item, complex) else (item, 0.0))
    return roots + cleaned


def solve(a, b=None):
    poly = polynomial(a)
    if b is not None:
        poly = poly - polynomial(b)
    return _companion_roots(poly.coef)


def summary(object):
    slope = deriv(object)
    return {
        "zeros": solve(object),
        "stationaryPoints": solve(slope),
        "inflexionPoints": solve(deriv(slope)),
    }


def change_origin(p, o):
    if not is_polynomial(p):
        raise TypeError("argument is not a polynomial")
    origin = float(o[0] if isinstance(o, (list, tuple)) else o)
    values = [predict(p, origin)]
    current = deriv(p)
    step = 1
    while current != polynomial(0):
        values.append(predict(current, origin))
        step += 1
        current = polynomial([item / step for item in coef(deriv(current))])
    return polynomial(values)


def _is_zero(p):
    return polynomial(p) == polynomial(0)


def _degree(p):
    return len(coef(p)) - 1


def _gcd2(x, y):
    if _is_zero(y):
        return polynomial(x)
    if _degree(y) == 0:
        return polynomial(1)
    return _gcd2(y, x % y)


def _lcm2(x, y):
    if _is_zero(x) or _is_zero(y):
        return polynomial(0)
    return (x / _gcd2(x, y)) * y


def _accumulate(func, init, items, right=True):
    if len(items) == 0:
        return init
    if right:
        return func(items[0], _accumulate(func, init, items[1:], True))
    return _accumulate(func, func(init, items[0]), items[1:], False)


class Polylist(list):
    def __init__(self, items):
        super().__init__(as_polynomial(item) for item in items)


def polylist(*items):
    return Polylist(items)


def is_polylist(x):
    return isinstance(x, Polylist)


def as_polylist(x):
    if is_polylist(x):
        return x
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], (Polynomial, list, tuple)):
        return Polylist(x)
    return polylist(x)


def GCD(*args):
    items = []
    for arg in args:
        if is_polylist(arg):
            items.extend(arg)
        else:
            items.append(as_polynomial(arg))
    if len(items) < 2:
        raise RuntimeError("Need at least two polynomials.")
    return _accumulate(_gcd2, items[0], items[1:], False)


def LCM(*args):
    items = []
    for arg in args:
        if is_polylist(arg):
            items.extend(arg)
        else:
            items.append(as_polynomial(arg))
    if len(items) < 2:
        raise RuntimeError("Need at least two polynomials.")
    return _accumulate(_lcm2, items[0], items[1:], False)


def poly_calc(x, y=None, tol=_TOL):
    xs = [float(item) for item in x]
    if y is None:
        acc = [1.0]
        for xi in xs:
            grown = [0.0] + acc
            scaled = [xi * item for item in acc] + [0.0]
            acc = [a - b for a, b in zip(grown, scaled)]
        return polynomial(acc)
    ys = [float(item) for item in y]
    paired = {}
    for xi, yi in zip(xs, ys):
        paired.setdefault(xi, []).append(yi)
    xs, ys = [], []
    for xi, values in paired.items():
        if max(values) - min(values) > tol and len(values) > 1:
            pass
        xs.append(xi)
        ys.append(values[0])
    if len(xs) <= 1:
        return polynomial(ys or [0.0])
    total = [0.0]
    for i, xi in enumerate(xs):
        others = xs[:i] + xs[i + 1:]
        basis = coef(poly_calc(others))
        scale = ys[i] / math.prod(xi - item for item in others)
        width = max(len(total), len(basis))
        left = total + [0.0] * (width - len(total))
        right = [scale * item for item in basis] + [0.0] * (width - len(basis))
        total = [a + b for a, b in zip(left, right)]
    total = [0.0 if abs(item) < tol else item for item in total]
    return polynomial(total)


def poly_from_zeros(*roots):
    flat = []
    for root in roots:
        if isinstance(root, (list, tuple)):
            flat.extend(root)
        else:
            flat.append(root)
    return poly_calc(flat)


poly_from_roots = poly_from_zeros
poly_from_values = poly_calc


def _poly_alpha_norm2(x, degree):
    values = np.asarray(list(x), dtype=float)
    center = float(values.mean())
    shifted = values - center
    vandermonde = np.column_stack([shifted ** power for power in range(degree + 1)])
    q_factor, r_factor = np.linalg.qr(vandermonde, mode="reduced")
    scaled = q_factor * np.diag(r_factor)
    norm2 = np.sum(scaled ** 2, axis=0)
    alpha = np.sum(shifted[:, None] * scaled ** 2, axis=0) / norm2 + center
    return alpha[:degree], np.concatenate(([1.0], norm2))


def poly_orth(x, degree=None, norm=True):
    points = [float(item) for item in x]
    if degree is None:
        degree = len(set(points)) - 1
    alpha, norm2 = _poly_alpha_norm2(points, degree)
    variable = polynomial()
    built = [polynomial(0), polynomial(1)]
    for j in range(degree):
        term = (variable - float(alpha[j])) * built[j + 1] - (float(norm2[j + 1]) / float(norm2[j])) * built[j]
        built.append(term)
    built = built[1:]
    if norm:
        scales = np.sqrt(norm2[1:])
        built = [item / float(scales[j]) for j, item in enumerate(built)]
    return Polylist(built)


def _curve(p, xlim=None, len_=1000):
    info = summary(p)
    interesting = [0.0]
    for key in ("zeros", "stationaryPoints", "inflexionPoints"):
        for value in info[key]:
            interesting.append(float(value.real) if isinstance(value, complex) else float(value))
    if xlim is None:
        xlim = [min(interesting), max(interesting)]
    else:
        xlim = [float(item) for item in xlim]
    if len(xlim) > 2:
        xs = xlim
    else:
        if xlim[1] == xlim[0]:
            xlim = [xlim[0] - 0.5, xlim[1] + 0.5]
        eps = (xlim[1] - xlim[0]) / 100.0
        xlim = [xlim[0] - eps, xlim[1] + eps]
        xs = list(np.linspace(xlim[0], xlim[1], int(len_)))
    return xs, predict(p, xs)


def plot_polynomial(p, xlim=None, ylim=None, len_=1000):
    """Draw the polynomial with Matplotlib. The check compares the curve values."""
    import matplotlib.pyplot as plt

    xs, ys = _curve(p, xlim, len_)
    drawn = list(ys)
    if ylim is not None:
        low, high = ylim
        drawn = [value if low <= value <= high else math.nan for value in drawn]
    figure = plt.figure()
    plt.plot(xs, drawn)
    plt.grid(True, linestyle="dashed")
    plt.xlabel("x")
    plt.ylabel("P(x)")
    plt.close(figure)
    return xs, drawn
