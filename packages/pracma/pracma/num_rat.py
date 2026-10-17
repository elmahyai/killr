"""Continued-fraction strings."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, r_length


def _continued(x, tol=1e-6):
    sign = float(np.sign(x))
    value = abs(float(x))
    term = math.floor(value)
    terms = [term]
    remainder = value - term
    matrix = np.array([[term, 1.0], [1.0, 0.0]])
    while abs(value - matrix[0, 0] / matrix[1, 0]) > tol:
        term = math.floor(1.0 / remainder)
        terms.append(term)
        remainder = 1.0 / remainder - term
        matrix = matrix @ np.array([[term, 1.0], [1.0, 0.0]])
    return sign * np.array(terms, dtype=float), np.array([sign * matrix[0, 0], matrix[1, 0]])


def _format_cf(terms):
    text = f"[ {int(terms[0]) if terms[0] == int(terms[0]) else terms[0]}"
    if terms.size >= 2:
        second = terms[1]
        text += f"; {int(second) if second == int(second) else second}"
    if terms.size >= 3:
        for term in terms[2:]:
            text += f", {int(term) if term == int(term) else term}"
        text += "]"
    return text


def rat(x, tol=1e-6):
    if r_length(x) == 0:
        return None
    if not is_r_numeric(x):
        raise PracmaError("Argument 'x' must be a numeric vector.")
    values = np.asarray(x, dtype=float).reshape(-1)
    return [_format_cf(_continued(value, tol)[0]) for value in values]


def rats(x, tol=1e-6):
    if r_length(x) == 0:
        return None
    if not is_r_numeric(x):
        raise PracmaError("Argument 'x' must be a numeric vector.")
    values = np.asarray(x, dtype=float).reshape(-1)
    numbers = np.zeros(values.size)
    for index, value in enumerate(values):
        fraction = _continued(value, tol)[1]
        text = f"{_trim(fraction[0])}/{_trim(fraction[1])}"
        print(text)
        numbers[index] = fraction[0] / fraction[1]
    return numbers


def _trim(value):
    number = float(value)
    if number == int(number):
        return str(int(number))
    return str(number)
