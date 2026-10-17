"""Checks that do not need R. The recorded comparisons live in translation.json."""

import math

import numpy as np

from pracma import Diag, Mode, conv, dot, factors, isprime, linspace, primes, sinc, sind, std, std_err


def test_linspace_includes_both_ends():
    assert np.allclose(linspace(0, 1, 5), [0, 0.25, 0.5, 0.75, 1])


def test_primes_below_two_is_none():
    assert primes(1) is None
    assert list(primes(10)) == [2, 3, 5, 7]


def test_factors_and_isprime():
    assert list(factors(360)) == [2, 2, 2, 3, 3, 5]
    assert list(isprime([0, 1, 2, 4, 17])) == [0, 0, 1, 0, 1]


def test_sind_of_thirty_is_one_half():
    assert abs(float(sind(30)[0]) - 0.5) < 1e-12


def test_sinc_of_zero_is_nan():
    assert math.isnan(float(sinc(0)[0]))


def test_sample_standard_deviation():
    assert abs(float(std([1, 2, 3], 0)[0]) - 1.0) < 1e-12


def test_std_err_of_a_vector_uses_the_sample_variance():
    assert abs(float(std_err([1, 2, 3, 4, 5])[0]) - math.sqrt(0.5)) < 1e-12


def test_conv_matches_the_polynomial_product():
    assert np.allclose(conv([1, 2, 3], [4, 5]), [4, 13, 22, 15])


def test_dot_of_a_matrix_is_one_sum_per_column():
    matrix = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    assert np.allclose(dot(matrix, matrix), [5, 25, 61])


def test_diag_offset_and_mode():
    placed = Diag([1, 2, 3], 1)
    assert placed.shape == (4, 4)
    assert placed[0, 1] == 1 and placed[2, 3] == 3
    assert Mode([1, 2, 2, 3, 3, 3, 1]) == 3
