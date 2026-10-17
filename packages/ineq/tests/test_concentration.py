"""Checks for Herfindahl, Rosenbluth, and conc."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ineq.concentration import Herfindahl, Rosenbluth, conc

# ineq 0.2-13 example vector, and the values printed by that package.
SALES = [541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261]
HERFINDAHL_SALES = 0.18408123091548528
ROSENBLUTH_SALES = 0.18590509587572451
TOLERANCE = 1e-8


def test_herfindahl_matches_the_sales_example():
    assert Herfindahl(SALES) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)
    assert Herfindahl(SALES, parameter=1) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)
    assert Herfindahl(SALES, parameter=None) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)
    assert Herfindahl(SALES, parameter=2) == pytest.approx(0.21663955132733032, abs=TOLERANCE)
    assert Herfindahl(SALES, parameter=0.5) == pytest.approx(0.16462407461875339, abs=TOLERANCE)


def test_rosenbluth_matches_the_sales_example():
    assert Rosenbluth(SALES) == pytest.approx(ROSENBLUTH_SALES, abs=TOLERANCE)


def test_conc_matches_both_measures_on_the_sales_example():
    assert conc(SALES) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)
    assert conc(SALES, type="Rosenbluth") == pytest.approx(ROSENBLUTH_SALES, abs=TOLERANCE)
    assert conc(SALES, parameter=2) == pytest.approx(Herfindahl(SALES, parameter=2), abs=TOLERANCE)
    assert conc(SALES, parameter=2, type="Rosenbluth") == pytest.approx(
        ROSENBLUTH_SALES, abs=TOLERANCE
    )
    assert conc(SALES, parameter=None) == pytest.approx(Herfindahl(SALES), abs=TOLERANCE)


@pytest.mark.parametrize("label", ["H", "Her", "Herfindahl"])
def test_conc_accepts_a_herfindahl_prefix(label):
    assert conc(SALES, type=label) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)


@pytest.mark.parametrize("label", ["R", "Ros", "Rosenbluth"])
def test_conc_accepts_a_rosenbluth_prefix(label):
    assert conc(SALES, type=label) == pytest.approx(ROSENBLUTH_SALES, abs=TOLERANCE)


def test_conc_null_type_uses_herfindahl():
    assert conc(SALES, type=None) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)


@pytest.mark.parametrize("label", ["nope", "", "h", "r", "X", "Herfindahlx"])
def test_conc_rejects_an_unknown_type(label):
    with pytest.raises(ValueError):
        conc(SALES, type=label)


def test_conc_rejects_a_non_string_type():
    with pytest.raises(ValueError):
        conc(SALES, type=1)


def test_rosenbluth_sorts_ascending_and_weights_from_n_down_to_one():
    # Sorted (1, 2, 3) with weights (3, 2, 1): 1 / (2 * (3 + 4 + 3) / 6 - 1) = 3/7.
    values = np.array([3.0, 1.0, 2.0])
    assert Rosenbluth(values) == pytest.approx(3 / 7, abs=TOLERANCE)
    assert values.tolist() == [3.0, 1.0, 2.0]
    assert Herfindahl([1.0, 2.0, 3.0]) == pytest.approx(14 / 36, abs=TOLERANCE)


def test_na_rm_false_returns_nan():
    assert math.isnan(Herfindahl([1.0, np.nan, 3.0], na_rm=False))
    assert math.isnan(Rosenbluth([1.0, np.nan], na_rm=False))
    assert math.isnan(conc([1.0, np.nan], na_rm=False))
    assert math.isnan(conc([1.0, np.nan], type="R", na_rm=False))


def test_na_rm_drops_missing_values():
    assert Herfindahl([541.0, np.nan, 2445.0]) == pytest.approx(0.70329387106339958, abs=TOLERANCE)
    assert Rosenbluth([2445.0, np.nan, 541.0]) == pytest.approx(
        0.73402163225172079, abs=TOLERANCE
    )
    assert conc([541.0, np.nan, 2445.0], na_rm=True) == pytest.approx(
        Herfindahl([541.0, 2445.0]), abs=TOLERANCE
    )
    assert conc([2445.0, np.nan, 541.0], type="Rosenbluth") == pytest.approx(
        Rosenbluth([541.0, 2445.0]), abs=TOLERANCE
    )


def test_all_missing_values_follow_the_empty_vector():
    assert math.isnan(Herfindahl([np.nan, np.nan], na_rm=False))
    assert Herfindahl([np.nan, np.nan], na_rm=True) == 0.0
    assert math.isnan(Rosenbluth([np.nan], na_rm=False))
    assert Rosenbluth([np.nan], na_rm=True) == -1.0


def test_empty_zero_and_single_inputs_match_r():
    assert Herfindahl([]) == 0.0
    assert Rosenbluth([]) == -1.0
    assert math.isnan(Herfindahl([0.0, 0.0, 0.0]))
    assert math.isnan(Rosenbluth([0.0, 0.0]))
    assert Herfindahl([5.0]) == 1.0
    assert Rosenbluth([5.0]) == 1.0
    assert Herfindahl([1.0, 2.0, 3.0], parameter=0) == pytest.approx(1.0, abs=TOLERANCE)


def test_column_vector_is_treated_as_a_vector():
    column = np.array(SALES, dtype=float).reshape(-1, 1)
    assert Herfindahl(column) == pytest.approx(HERFINDAHL_SALES, abs=TOLERANCE)
    assert Rosenbluth(column) == pytest.approx(ROSENBLUTH_SALES, abs=TOLERANCE)
