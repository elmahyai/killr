"""Primes, factors, and binomial coefficients."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError


def primes(n):
    if not isinstance(n, (int, float, np.integer, np.floating)) or isinstance(n, bool):
        array = np.asarray(n)
        if array.size != 1 or not np.issubdtype(array.dtype, np.number):
            raise PracmaError("Argument 'n' must be a numeric scalar.")
        n = float(array.reshape(-1)[0])
    limit = math.floor(float(n))
    if limit < 2:
        return None
    values = list(range(1, limit + 1, 2))
    count = len(values)
    values[0] = 2
    if limit >= 9:
        k = 3
        while k <= math.sqrt(limit):
            if values[(k + 1) // 2 - 1] != 0:
                index = (k * k + 1) / 2
                while index <= count:
                    values[int(index) - 1] = 0
                    index += k
            k += 2
    return np.array([item for item in values if item > 0], dtype=float)


def factors(n):
    number = float(np.asarray(n).reshape(-1)[0]) if not isinstance(n, (int, float)) else float(n)
    if number != round(number) or number < 1:
        raise PracmaError("Argument 'n' must be a nonnegative integer.")
    if number >= 2**53:
        raise PracmaError("Argument 'n' must not be larger than 2^53-1.")
    if number < 4:
        return np.array([number])
    found = []
    candidates = primes(math.sqrt(number))
    divisors = candidates[number % candidates == 0]
    if divisors.size == 0:
        return np.array([number])
    for prime in divisors:
        prime = float(prime)
        while number % prime == 0:
            found.append(prime)
            number /= prime
    if number > 1:
        found.append(number)
    return np.array(found, dtype=float)


def isprime(x):
    if x is None or np.asarray(x).size == 0:
        raise PracmaError("Argument 'x' must be a nonempty vector or matrix.")
    values = np.asarray(x, dtype=float).reshape(-1)
    if np.any(values < 0) or np.any(values != np.round(values)):
        raise PracmaError("All entries of 'x' must be nonnegative integers.")
    primes_under = primes(math.ceil(math.sqrt(float(np.max(values)))))
    if primes_under is None:
        primes_under = np.array([], dtype=float)
    flags = np.empty(values.size, dtype=float)
    for index, item in enumerate(values):
        below = primes_under[primes_under < item]
        flags[index] = 1.0 if below.size == 0 or np.all(item % below != 0) else 0.0
    flags[(values == 0) | (values == 1)] = 0.0
    return flags


def nchoosek(n, k):
    left = float(n)
    right = float(k)
    if left < 0 or right < 0 or left != math.floor(left) or right != math.floor(right):
        raise PracmaError("n and k must be nonnegative integers")
    if right > left:
        raise PracmaError("Argument 'k' must be an integer between 0 and 'n'.")
    return float(math.comb(int(left), int(right)))
