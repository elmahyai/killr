"""Checks for the empirical Lorenz routines against ineq 0.2-13."""

from __future__ import annotations

import numpy as np
import pytest

from ineq.lorenz import Lasym, Lc, lc_mehran, major

USA_X = np.array(
    [541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261],
    dtype=np.float64,
)
USA_N = np.array(
    [482, 825, 722, 690, 661, 760, 745, 2140, 1911, 1024],
    dtype=np.float64,
)
USA_Y = np.array(
    [841, 2063, 2445, 3438, 4437, 5401, 6392, 8304, 11304, 21961],
    dtype=np.float64,
)


def test_lc_matches_grouped_usa_income():
    curve = Lc(USA_X, n=USA_N, plot=False)
    assert list(curve) == ["p", "L", "L.general"]
    expected_p = np.array(
        [
            0,
            0.048393574297188754,
            0.13122489959839356,
            0.203714859437751,
            0.27299196787148594,
            0.3393574297188755,
            0.41566265060240964,
            0.49046184738955823,
            0.70532128514056225,
            0.89718875502008033,
            1,
        ]
    )
    expected_l = np.array(
        [
            0,
            0.0032304800766785905,
            0.018183228907218092,
            0.040052727432923332,
            0.069441248181722953,
            0.10577528499018178,
            0.15662757711689967,
            0.21562265824201191,
            0.43577528796344944,
            0.71759824593066202,
            1,
        ]
    )
    expected_g = np.array(
        [
            0,
            26.180923694779118,
            147.36315261044174,
            324.60110441767068,
            562.77580321285143,
            857.23935742971889,
            1269.3638554216868,
            1747.4803212851407,
            3531.6730923694781,
            5815.6634538152612,
            8104.3445783132529,
        ]
    )
    assert curve["p"] == pytest.approx(expected_p, abs=1e-8)
    assert curve["L"] == pytest.approx(expected_l, abs=1e-8)
    assert curve["L.general"] == pytest.approx(expected_g, abs=1e-8)


def test_lc_generalized_uses_means_after_frequency_scaling():
    curve = Lc(USA_X, n=USA_N)
    order = np.argsort(USA_X, kind="mergesort")
    scaled = USA_N[order] * USA_X[order]
    weights = USA_N[order]
    assert curve["L.general"] == pytest.approx(
        curve["L"] * (np.mean(scaled) / np.mean(weights)),
        abs=1e-8,
    )


def test_lc_default_weights_are_ones_before_dropping_missing():
    curve = Lc(np.array([3.0, np.nan, 1.0, 2.0]))
    assert curve["p"] == pytest.approx([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0], abs=1e-8)
    assert curve["L"] == pytest.approx([0.0, 1.0 / 6.0, 0.5, 1.0], abs=1e-8)
    assert curve["L.general"] == pytest.approx([0.0, 1.0 / 3.0, 1.0, 2.0], abs=1e-8)


def test_lc_aligns_frequencies_before_dropping_missing_x():
    curve = Lc(
        np.array([3.0, np.nan, 1.0, 2.0]),
        n=np.array([10.0, 20.0, 30.0, 40.0]),
    )
    assert curve["p"] == pytest.approx([0.0, 0.375, 0.875, 1.0], abs=1e-8)
    assert curve["L"] == pytest.approx(
        [0.0, 0.21428571428571427, 0.7857142857142857, 1.0],
        abs=1e-8,
    )
    assert curve["L.general"] == pytest.approx(
        [0.0, 0.375, 1.375, 1.75],
        abs=1e-8,
    )


def test_lc_keeps_tied_values_in_input_order():
    curve = Lc(np.array([1.0, 2.0, 1.0]), n=np.array([10.0, 20.0, 30.0]))
    assert curve["p"] == pytest.approx(
        [0.0, 1.0 / 6.0, 2.0 / 3.0, 1.0],
        abs=1e-8,
    )
    assert curve["L"] == pytest.approx([0.0, 0.125, 0.5, 1.0], abs=1e-8)
    assert curve["L.general"] == pytest.approx(
        [0.0, 1.0 / 6.0, 2.0 / 3.0, 4.0 / 3.0],
        abs=1e-8,
    )


def test_lc_mehran_matches_grouped_usa_income():
    curve = lc_mehran(USA_X, USA_N)
    assert list(curve) == ["p", "L"]
    expected_p = np.array(
        [
            0.0,
            -0.0,
            0.048393574297188768,
            0.13122489959839359,
            0.20371485943775103,
            0.27299196787148583,
            0.3393574297188755,
            0.41566265060240976,
            0.63079094316307327,
            1.0,
            1.0,
        ]
    )
    expected_l = np.array(
        [
            0.0,
            0.0,
            0.0032304800766785914,
            0.018183228907218095,
            0.040052727432923339,
            0.069441248181722898,
            0.10577528499018178,
            0.15662757711689973,
            0.32630200701804779,
            0.86861169907478852,
            1.0,
        ]
    )
    assert curve["p"] == pytest.approx(expected_p, abs=1e-8)
    assert curve["L"] == pytest.approx(expected_l, abs=1e-8)


def test_lc_mehran_two_and_three_classes():
    two = lc_mehran(np.array([1.0, 3.0]), np.array([2.0, 2.0]))
    assert two["p"] == pytest.approx([0.0, 0.0, 1.0, 1.0], abs=1e-8)
    assert two["L"] == pytest.approx([0.0, 0.0, 0.5, 1.0], abs=1e-8)
    three = lc_mehran(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 1.0]))
    assert three["p"] == pytest.approx(
        [0.0, 0.0, 1.0 / 3.0, 1.0, 1.0],
        abs=1e-8,
    )
    assert three["L"] == pytest.approx(
        [0.0, 0.0, 1.0 / 6.0, 0.83333333333333348, 1.0],
        abs=1e-8,
    )


def test_lasym_on_grouped_usa_income_and_damgaard_samples():
    assert Lasym(USA_X, USA_N) == pytest.approx(0.70626655568319618, abs=1e-8)
    plant_x = np.repeat([50.0 / 9.0, 50.0], [9, 1])
    plant_y = np.repeat([2.0, 18.0], [5, 5])
    assert Lasym(plant_x) == pytest.approx(1.46, abs=1e-8)
    assert Lasym(plant_y) == pytest.approx(0.74, abs=1e-8)
    assert Lasym(plant_x, interval=True) == pytest.approx(1.46, abs=1e-8)


def test_lasym_interval_when_an_observation_equals_the_mean():
    sample = np.array([1.0, 2.0, 3.0])
    assert Lasym(sample) == pytest.approx(0.83333333333333326, abs=1e-8)
    assert Lasym(sample, interval=True) == pytest.approx(
        [0.5, 1.1666666666666665],
        abs=1e-8,
    )
    assert Lasym(np.array([5.0, 5.0, 5.0]), interval=True) == pytest.approx(
        [0.0, 2.0],
        abs=1e-8,
    )


def test_lasym_weights_follow_r_indexing_after_na_omit():
    # na.omit shortens x, then order indexes the original n.
    skewed = Lasym(np.array([1.0, np.nan, 3.0]), n=np.array([1.0, 100.0, 1.0]))
    assert skewed == pytest.approx(0.032894306173487653, abs=1e-8)
    assert Lasym(np.array([1.0, 3.0, 1.0]), n=np.array([4.0, 1.0, 2.0])) == pytest.approx(
        1.5918367346938775,
        abs=1e-8,
    )


def test_lasym_returns_nan_when_missing_values_are_kept():
    missing = np.array([1.0, np.nan, 3.0])
    assert np.isnan(Lasym(missing, na_rm=False)).all()
    assert Lasym(missing, na_rm=False).shape == (1,)
    both = Lasym(missing, na_rm=False, interval=True)
    assert both.shape == (2,)
    assert np.isnan(both).all()


def test_major_true_false_and_incomparable():
    assert major(USA_X, USA_Y) is True
    assert major(USA_Y, USA_X) is False
    assert major(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])) is True
    with pytest.raises(ValueError, match="^incomparable arguments$"):
        major(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 4.0]))
    with pytest.raises(ValueError, match="^incomparable arguments$"):
        major(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))
