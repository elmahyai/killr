"""censboot against CRAN boot 1.3-32, set.seed(1), tolerance 1e-8."""

import numpy as np
import pytest

from boot.censored import censboot
from boot.rng import set_seed

TOLERANCE = 1e-8

_DATA = np.array(
    [
        [1.2, 1.0],
        [3.4, 1.0],
        [0.5, 0.0],
        [2.2, 1.0],
        [8.1, 0.0],
        [4.0, 1.0],
        [6.5, 1.0],
        [1.1, 0.0],
    ]
)

# boot::censboot, set.seed(1), statistic = mean of column 1, R = 30, sim = "ordinary".
_ORDINARY = np.array(
    [
        2.875,
        3.0874999999999999,
        3.7124999999999999,
        2.3624999999999998,
        4.3499999999999996,
        5.0625,
        4.375,
        2.625,
        2.8999999999999999,
        3.0,
        2.9125000000000001,
        2.8250000000000002,
        3.1749999999999998,
        3.2250000000000001,
        3.7875000000000001,
        3.875,
        3.2999999999999998,
        3.8624999999999998,
        3.4500000000000002,
        3.8500000000000001,
        3.5874999999999999,
        4.0250000000000004,
        4.9375,
        3.5749999999999997,
        3.4749999999999996,
        2.9125000000000001,
        3.2749999999999999,
        2.6375000000000002,
        3.0750000000000002,
        2.6499999999999999,
    ]
)

# Same seed, two strata of three, statistic = sum of column 1, R = 15.
_STRATA_DATA = np.array(
    [[1.0, 1.0], [2.0, 0.0], [3.0, 1.0], [4.0, 1.0], [8.0, 0.0], [5.0, 1.0]]
)
_STRATA = np.array([18.0, 20, 23, 30, 19, 22, 26, 22, 23, 27, 19, 19, 22, 23, 26])

_F = {"time": np.array([1.0, 3.0, 5.0]), "surv": np.array([0.8, 0.4, 0.0])}
_G = {"time": np.array([2.0, 4.0, 6.0]), "surv": np.array([0.7, 0.3, 0.0])}

# sim = "cond", R = 8, statistic = c(mean(time), sum(event)).
_COND = np.array(
    [
        [3.0, 4.0],
        [2.66666666666667, 4.0],
        [2.66666666666667, 4.0],
        [3.33333333333333, 4.0],
        [2.66666666666667, 4.0],
        [2.83333333333333, 5.0],
        [3.33333333333333, 4.0],
        [4.0, 4.0],
    ]
)

# sim = "weird", R = 6, statistic = mean(time).
_WEIRD_SURV = {
    "time": np.array([1.0, 3.0, 5.0]),
    "surv": np.array([0.8, 0.4, 0.1]),
    "n.risk": np.array([6.0, 4.0, 2.0]),
    "n.event": np.array([1.0, 1.0, 1.0]),
}
_WEIRD = np.array([4.5, 3.6666666666666665, 3.0, 4.0, 4.0, 3.8571428571428572])

# sim = "model" with a coefficient vector and linear predictors, R = 6.
_MODEL = np.array(
    [3.0, 3.0, 2.6666666666666665, 3.1666666666666665, 2.1666666666666665, 2.3333333333333335]
)


def _mean_time(data):
    return float(np.mean(np.asarray(data, dtype=float)[:, 0]))


def test_ordinary_matches_r():
    set_seed(1)
    out = censboot(_DATA, _mean_time, 30, sim="ordinary")
    assert out.t0.shape == (1,)
    assert abs(float(out.t0[0]) - 3.375) <= TOLERANCE
    assert out.t.shape == (30, 1)
    assert np.max(np.abs(out.t[:, 0] - _ORDINARY)) <= TOLERANCE
    assert out.R == 30
    assert out.sim == "ordinary"
    assert out.statistic is _mean_time
    assert np.array_equal(out.data, _DATA)
    assert np.array_equal(out.strata, np.ones(8))
    assert out.seed.dtype == np.int32
    assert out.seed.shape == (626,)
    assert int(out.seed[0]) == 10403
    assert int(out.seed[1]) == 624


def test_stratified_ordinary_matches_r():
    set_seed(1)
    out = censboot(_STRATA_DATA, lambda data: float(np.sum(data[:, 0])), 15, strata=np.array([1, 1, 1, 2, 2, 2]))
    assert abs(float(out.t0[0]) - 23.0) <= TOLERANCE
    assert np.max(np.abs(out.t[:, 0] - _STRATA)) <= TOLERANCE
    assert np.array_equal(out.strata, np.array([1.0, 1, 1, 2, 2, 2]))


def test_model_without_cox_is_ordinary():
    set_seed(1)
    out = censboot(_STRATA_DATA, _mean_time, 5, sim="model")
    assert out.sim == "ordinary"
    expected = np.array([2.1666666666666665, 3.6666666666666665, 3.6666666666666665, 4.0, 6.0])
    assert np.max(np.abs(out.t[:, 0] - expected)) <= TOLERANCE


def test_cond_weird_and_model_match_r():
    def both(data):
        values = np.asarray(data, dtype=float)
        return np.array([np.mean(values[:, 0]), np.sum(values[:, 1])])

    set_seed(1)
    cond = censboot(_STRATA_DATA, both, 8, F_surv=_F, G_surv=_G, sim="cond")
    assert cond.sim == "cond"
    assert np.max(np.abs(cond.t0 - np.array([3.8333333333333335, 4.0]))) <= TOLERANCE
    assert np.max(np.abs(cond.t - _COND)) <= TOLERANCE
    assert cond.strata.shape == (6, 2)

    set_seed(1)
    weird = censboot(_STRATA_DATA, _mean_time, 6, F_surv=_WEIRD_SURV, sim="weird")
    assert weird.sim == "weird"
    assert abs(float(weird.t0[0]) - 3.8333333333333335) <= TOLERANCE
    assert np.max(np.abs(weird.t[:, 0] - _WEIRD)) <= TOLERANCE
    assert weird.data.shape == (6, 2)

    cox = type("Cox", (), {})()
    cox.coefficients = np.array([0.2])
    cox.linear_predictors = np.array([0.1, -0.2, 0.1, -0.2, 0.0, 0.3])
    set_seed(1)
    model = censboot(_STRATA_DATA, _mean_time, 6, F_surv=_F, G_surv=_G, cox=cox, sim="model")
    assert model.sim == "model"
    assert abs(float(model.t0[0]) - 3.8333333333333335) <= TOLERANCE
    assert np.max(np.abs(model.t[:, 0] - _MODEL)) <= TOLERANCE


def test_errors():
    with pytest.raises(ValueError, match="missing values not allowed"):
        censboot(np.array([[1.0, 1.0], [np.nan, 0.0]]), _mean_time, 2)
    with pytest.raises(ValueError, match="unknown value of 'sim'"):
        censboot(_DATA, _mean_time, 2, sim="foo")
    with pytest.raises(ValueError, match="'F.surv' is required"):
        censboot(_DATA, _mean_time, 2, sim="weird")
    with pytest.raises(ValueError, match="'G.surv' is required"):
        censboot(_DATA, _mean_time, 2, sim="cond", F_surv={"time": [1.0], "surv": [0.0]})
    with pytest.raises(ValueError, match="'index' must contain 2 elements"):
        censboot(_DATA, _mean_time, 2, index=[1])
    with pytest.raises(ValueError, match="cannot be used with a \"coxph\" object"):
        censboot(_DATA, _mean_time, 2, sim="weird", F_surv=_WEIRD_SURV, cox={"coefficients": [0.1]})
