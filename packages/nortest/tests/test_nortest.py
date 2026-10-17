"""Checks against nortest 1.0-4."""

import math
import warnings

import pytest

from nortest import ad_test, cvm_test, lillie_test, pearson_test, sf_test

TOLERANCE = 1e-8
SAMPLE = [2.1, 3.4, float("nan"), 1.2, 5.6, 4.0, 3.3, 2.8, 6.1, 1.9, float("nan"), 4.4]
UNIFORM = list(range(1, 31))
SEPARATED = [0.0] * 20 + [100.0] * 20


def test_ad_matches_the_sample():
    result = ad_test(SAMPLE)
    assert result.statistic == pytest.approx(0.17223562895629918, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.90092969835788672, abs=TOLERANCE)
    assert result.data_name == "SAMPLE"


def test_cvm_matches_the_sample():
    result = cvm_test(SAMPLE)
    assert result.statistic == pytest.approx(0.022588848772697193, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.92686165238523155, abs=TOLERANCE)


def test_lillie_matches_the_sample():
    result = lillie_test(SAMPLE)
    assert result.statistic == pytest.approx(0.12014249041020342, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.95017720180034493, abs=TOLERANCE)


def test_pearson_matches_the_sample():
    result = pearson_test(SAMPLE)
    assert result.statistic == pytest.approx(2.0, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.57240670447087916, abs=TOLERANCE)
    assert result.extra["n_classes"] == 6
    assert result.extra["df"] == 3


def test_pearson_without_adjustment_uses_two_more_degrees():
    result = pearson_test(SAMPLE, adjust=False)
    assert result.p_value == pytest.approx(0.84914503608460967, abs=TOLERANCE)
    assert result.extra["df"] == 5


def test_pearson_class_count_is_honored():
    result = pearson_test(SAMPLE, n_classes=4)
    assert result.statistic == pytest.approx(0.4, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.52708925686553809, abs=TOLERANCE)
    assert result.extra["n_classes"] == 4
    assert result.extra["df"] == 1


def test_sf_matches_the_sample():
    result = sf_test(SAMPLE)
    assert result.statistic == pytest.approx(0.97737319435907766, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.95431055832040768, abs=TOLERANCE)


def test_uniform_integers_match():
    assert ad_test(UNIFORM).statistic == pytest.approx(0.32100536119316914, abs=TOLERANCE)
    assert cvm_test(UNIFORM).p_value == pytest.approx(0.61771992973853629, abs=TOLERANCE)
    assert lillie_test(UNIFORM).statistic == pytest.approx(0.069849221810290629, abs=TOLERANCE)
    assert pearson_test(UNIFORM).p_value == pytest.approx(0.91688412025399013, abs=TOLERANCE)
    assert sf_test(UNIFORM).statistic == pytest.approx(0.97248388113019912, abs=TOLERANCE)


def test_separated_sample_uses_the_tail_formulas():
    assert ad_test(SEPARATED).p_value == pytest.approx(1.6407819955767314e-17, abs=TOLERANCE)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = cvm_test(SEPARATED)
    assert result.p_value == pytest.approx(7.37e-10, abs=TOLERANCE)
    assert result.statistic == pytest.approx(1.1450805546553409, abs=TOLERANCE)
    assert "7.37e-10" in str(caught[0].message)
    assert lillie_test(SEPARATED).p_value == pytest.approx(1.0033992154849462e-12, abs=TOLERANCE)
    assert sf_test(SEPARATED).statistic == pytest.approx(0.65384862848718506, abs=TOLERANCE)


def test_logical_values_are_zero_and_one():
    values = [True, False, True, False, True, False, True, False]
    result = ad_test(values)
    assert result.statistic == pytest.approx(1.2821103239214704, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.00097757020352872066, abs=TOLERANCE)


def test_sample_size_errors():
    with pytest.raises(ValueError, match="greater than 7"):
        ad_test(list(range(7)))
    with pytest.raises(ValueError, match="greater than 7"):
        cvm_test(list(range(7)))
    with pytest.raises(ValueError, match="greater than 4"):
        lillie_test(list(range(4)))
    with pytest.raises(ValueError, match="between 5 and 5000"):
        sf_test(list(range(4)))
    with pytest.raises(ValueError, match="between 5 and 5000"):
        sf_test(list(range(5001)))


def test_zero_sd_follows_r():
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        ad_test([1.0] * 10)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = sf_test([1.0] * 10)
    assert math.isnan(result.statistic)
    assert math.isnan(result.p_value)
    assert "standard deviation is zero" in str(caught[0].message)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = pearson_test([1.0] * 20)
    assert result.statistic == pytest.approx(20.0, abs=TOLERANCE)
    assert result.p_value == pytest.approx(0.00049939922738733355, abs=TOLERANCE)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = pearson_test(list(range(1, 9)), n_classes=2)
    assert result.statistic == pytest.approx(0.0, abs=TOLERANCE)
    assert math.isnan(result.p_value)
    assert "NaNs produced" in str(caught[0].message)


def test_print_matches_the_htest_layout():
    text = str(ad_test(SAMPLE))
    assert text == (
        "\n\tAnderson-Darling normality test\n\n"
        "data:  SAMPLE\n"
        "A = 0.17224, p-value = 0.9009\n\n"
    )
    assert "p-value < 2.2e-16" in str(ad_test(SEPARATED))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert "P = 0, p-value = NA" in str(pearson_test(list(range(1, 9)), n_classes=2))


def test_data_name_keeps_a_list_literal():
    result = ad_test([1, 2, 3, 4, 5, 6, 7, 8])
    assert result.data_name == "[1, 2, 3, 4, 5, 6, 7, 8]"
