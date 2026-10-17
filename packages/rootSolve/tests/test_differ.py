"""Checks against rootSolve 1.8.2.4."""

import math

import numpy as np
import pytest

from rootSolve import gradient, hessian, jacobian_band, jacobian_full, uniroot_all

TOLERANCE = 1e-8


def logistic(x, times):
    n0 = x["N0"]
    rate = x["r"]
    carrying = x["K"]
    return [
        carrying / (1 + (carrying - n0) / n0 * math.exp(-rate * time))
        for time in times
    ]


def squares(x):
    return sum(value * value for value in x)


def product(x):
    return [x["a"] ** 2, x["a"] * x["b"]]


def linear(time, y, parms):
    return [-0.1 * y[0] + 0.02 * y[1], 0.1 * y[0] - 0.2 * y[1]]


def decay(time, y, parms):
    return [-0.1 * value for value in y]


def test_gradient_matches_the_logistic_sensitivity():
    values = gradient(logistic, {"N0": 76.1, "r": 0.02, "K": 500}, times=list(range(6)))
    expected = np.array(
        [
            0.99999997536531893,
            1.0139566219790255,
            1.0280004571349992,
            1.0421282128968732,
            1.0563364532629815,
            1.0706216862098927,
            0,
            65.418028327712818,
            132.64820495351159,
            201.70677430542128,
            272.60909405413258,
            345.36960669129257,
            -2.8421709430404003e-09,
            0.00047449191242776573,
            0.00097184624792134844,
            0.0014927820757293373,
            0.002038021307271265,
            0.0026083228021889227,
        ]
    )
    assert values.data.ravel(order="F") == pytest.approx(expected, abs=TOLERANCE)
    assert values.colnames == ["N0", "r", "K"]


def test_centered_gradient_matches():
    values = gradient(
        logistic,
        {"N0": 76.1, "r": 0.02, "K": 500},
        centered=True,
        times=list(range(6)),
    )
    expected = np.array(
        [
            0.999999994039241,
            1.0139566406529474,
            1.0280004664719602,
            1.0421282128968732,
            1.0563364625999427,
            1.0706216862098927,
            0,
            65.418028327712818,
            132.64820424296886,
            201.70677146325033,
            272.6090905014189,
            345.36960100695069,
            0,
            0.00047449333351323725,
            0.00097184766900681996,
            0.0014927806546438658,
            0.0020380227283567365,
            0.0026083213811034511,
        ]
    )
    assert values.data.ravel(order="F") == pytest.approx(expected, abs=TOLERANCE)


def test_scalar_gradient_keeps_the_last_name():
    values = gradient(squares, {"a": 1.0, "b": 2.0})
    assert values.data.ravel(order="F") == pytest.approx(
        [1.9999999878450581, 3.9999999756901161], abs=TOLERANCE
    )
    assert values.rownames == ["b"]
    assert values.colnames == ["a", "b"]


def test_hessian_flattens_the_gradient_by_column():
    values = hessian(squares, {"a": 1.0, "b": -3.0})
    assert values.data.ravel(order="F") == pytest.approx(
        [-1.9999999656405976, 0, 0, -1.9999999878450578], abs=TOLERANCE
    )
    assert values.rownames is None
    assert values.colnames == ["a", "b"]


def test_hessian_centered_and_pert_follow_the_r_calls():
    centered = hessian(squares, [1.0, -3.0], centered=True)
    assert centered.data.ravel(order="F") == pytest.approx(
        [-0.99999998282029878, 0, 0, 1.4540272245492738], abs=TOLERANCE
    )
    wide = hessian(squares, {"a": 1.0, "b": -3.0}, pert=1e-4)
    assert wide.data.ravel(order="F") == pytest.approx(
        [2.0001555989246356, 0, 0, 1.9997661189001072], abs=TOLERANCE
    )


def test_vector_function_gradient_and_hessian():
    values = gradient(product, {"a": 2.0, "b": 3.0})
    assert values.data.ravel(order="F") == pytest.approx(
        [3.9999999756901161, 2.9999999817675871, 0, 1.9999999878450578],
        abs=TOLERANCE,
    )
    second = hessian(product, {"a": 2.0, "b": 3.0})
    assert second.data.ravel(order="F") == pytest.approx(
        [
            6.8817841203383523,
            2.9408920854123721,
            0,
            1.480297362466132,
            0,
            1.4802973661668752,
            0,
            0.32019826049870892,
        ],
        abs=TOLERANCE,
    )


def test_full_jacobian_matches_the_linear_model():
    values = jacobian_full({"A": 1.0, "B": 2.0}, linear)
    assert values.data.ravel(order="F") == pytest.approx(
        [
            -0.099999999947364415,
            0.10000000272292198,
            0.019999999920083944,
            -0.19999999989472883,
        ],
        abs=TOLERANCE,
    )
    assert values.colnames == ["A", "B"]
    forced = jacobian_full({"A": 1.0, "B": 2.0}, linear, dy=[0.0, 0.0])
    assert forced.data.ravel(order="F") == pytest.approx(
        [-6000000.1000000006, -29999999.900000002, -2999999.9800000004, -15000000.200000001],
        abs=TOLERANCE,
    )


def test_banded_jacobian_matches():
    values = jacobian_band({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}, decay)
    expected = np.array(
        [
            0,
            -0.099999999947364415,
            0,
            0,
            -0.099999999947364415,
            0,
            0,
            -0.099999999022178543,
            0,
            0,
            -0.099999999947364415,
            0,
        ]
    )
    assert values.data.ravel(order="F") == pytest.approx(expected, abs=TOLERANCE)
    assert values.shape == (3, 4)


def test_uniroot_all_matches_the_cosine_and_the_rate():
    roots = uniroot_all(lambda x: np.cos(2 * np.asarray(x, dtype=float)) ** 3, [0, 10])
    assert roots == pytest.approx(
        [
            0.78531307477361589,
            2.3561692084497214,
            3.9268588396098547,
            5.4977797120607637,
            7.0686230874908933,
            8.6392490680030782,
        ],
        abs=TOLERANCE,
    )

    def rate(x, r=0.05):
        arr = np.asarray(x, dtype=float)
        return r * arr * (1 - arr / 10) - 0.1 * arr**2 / (arr**2 + 1)

    assert uniroot_all(rate, [0, 10]) == pytest.approx(
        [0, 0.68336581873923841, 2, 7.3167115160978433], abs=TOLERANCE
    )
    assert uniroot_all(lambda x: np.asarray(x, dtype=float) - 1, [0, 2], n=2) == pytest.approx(
        [1.0], abs=TOLERANCE
    )


def test_errors_use_the_r_messages():
    with pytest.raises(ValueError, match="x-values should be numeric"):
        gradient(squares, "a")
    with pytest.raises(ValueError, match="y-values should be numeric"):
        jacobian_full("a", linear)
    with pytest.raises(ValueError, match="interval"):
        uniroot_all(lambda x: x, [0, 1, 2])
    with pytest.raises(ValueError, match="lower < upper"):
        uniroot_all(lambda x: x, lower=2, upper=1)
    with pytest.raises(ValueError, match="wrong sign"):
        jacobian_band({"A": 1.0, "B": 2.0}, linear, bandup=1, banddown=1)
