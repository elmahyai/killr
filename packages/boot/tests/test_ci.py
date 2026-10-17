"""Confidence intervals from boot 1.3-32, compared with fixed replicates."""

import math
import warnings

import numpy as np
import pytest

from boot.ci import _qnorm, _r_round, abc_ci, boot_ci, norm_ci, print_bootci

ATOL = 1e-8

HOURS = np.array(
    [3, 5, 7, 18, 43, 85, 91, 98, 100, 130, 230, 487], dtype=float
)


def _col(values, shape):
    return np.array(values, dtype=float).reshape(shape, order="F")


def _small_boot():
    data = np.array([2.3, 4.1, 3.3, 5.0, 4.4, 6.2, 3.8, 5.5])

    def statistic(d, w):
        mean = float(np.sum(d * w))
        variance = float(np.sum(w * (d - mean) ** 2) * len(d) / (len(d) - 1) / len(d))
        return np.array([mean, variance])

    replicates = np.column_stack(
        [
            [
                4.2, 4.0, 4.5, 3.9, 4.6, 4.1, 4.3, 3.8, 4.7, 4.15,
                4.55, 3.95, 4.25, 4.35, 4.05, 4.65, 3.85, 4.45, 4.12, 4.28,
            ],
            [
                0.18, 0.22, 0.15, 0.25, 0.14, 0.20, 0.17, 0.28, 0.13, 0.19,
                0.16, 0.24, 0.18, 0.17, 0.21, 0.14, 0.27, 0.16, 0.20, 0.18,
            ],
        ]
    )
    weights = np.full(data.size, 1.0 / data.size)
    return {
        "t0": statistic(data, weights),
        "t": replicates,
        "R": 20,
        "data": data,
        "statistic": statistic,
        "sim": "ordinary",
        "stype": "w",
        "strata": np.ones(data.size, dtype=int),
        "weights": weights,
        "boot_type": "boot",
    }


def _grid_boot():
    n = 30
    data = np.arange(1, n + 1, dtype=float) * 1.7

    def statistic(d, w):
        mean = math.fsum(np.asarray(d * w, dtype=float).reshape(-1))
        variance = math.fsum(np.asarray(w * (d - mean) ** 2, dtype=float).reshape(-1)) / len(d)
        return np.array([mean, variance])

    index = np.arange(1, 101)
    weights = np.full(n, 1.0 / n)
    center = statistic(data, weights)[0]
    replicates = np.column_stack(
        [center + ((index % 17) - 8) / 10.0, 0.3 + (index % 5) / 100.0]
    )
    return {
        "t0": statistic(data, weights),
        "t": replicates,
        "R": 100,
        "data": data,
        "statistic": statistic,
        "sim": "ordinary",
        "stype": "w",
        "strata": np.ones(n, dtype=int),
        "weights": weights,
        "boot_type": "boot",
    }


def _intervals(boot, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return boot_ci(boot, **kwargs)


def test_qnorm_matches_r_on_interval_probabilities():
    expected = {
        0.025: -1.9599639845400538,
        0.5: 0.0,
        0.975: 1.9599639845400536,
        1e-12: -7.0344838253011321,
        1.0 - 1e-12: 7.0344869100478356,
    }
    for probability, quantile in expected.items():
        assert abs(float(_qnorm(probability)) - quantile) <= ATOL
    assert _qnorm(0.0) == -math.inf
    assert _qnorm(1.0) == math.inf
    assert math.isnan(float(_qnorm(-0.1)))


def test_r_round_keeps_the_fractional_tie():
    assert _r_round(101 * 0.975, 2) == pytest.approx(98.47)
    assert _r_round(21 * 0.025, 2) == pytest.approx(0.52)


def test_norm_ci_aircondit_and_influence_variance():
    mean = float(np.mean(HOURS))
    interval = norm_ci(t0=mean, var_t0=mean ** 2 / HOURS.size)
    assert interval.shape == (1, 3)
    np.testing.assert_allclose(
        interval,
        [[0.95, 46.930554287633569, 169.2361123790331]],
        atol=ATOL,
        rtol=0,
    )
    logged = norm_ci(t0=math.log(mean), var_t0=1.0 / HOURS.size)
    transformed = np.exp(logged[0, 1:])
    np.testing.assert_allclose(
        transformed,
        [61.381572471320268, 190.31781810253719],
        atol=ATOL,
        rtol=0,
    )
    from_influence = norm_ci(t0=3.0, L=np.array([-2.0, -1.0, 0.0, 1.0, 2.0]))
    np.testing.assert_allclose(
        from_influence,
        [[0.95, 1.76040993539088, 4.23959006460912]],
        atol=ATOL,
        rtol=0,
    )


def test_boot_ci_fixed_replicates_match_r():
    result = _intervals(
        _small_boot(), conf=[0.90, 0.95], type=["norm", "basic", "stud", "perc", "bca"]
    )
    np.testing.assert_allclose(
        result.normal,
        _col(
            [
                0.9, 0.95,
                3.96327677893375, 3.87721751657273,
                4.86172322106625, 4.94778248342727,
            ],
            (2, 3),
        ),
        atol=ATOL,
        rtol=0,
    )
    np.testing.assert_allclose(
        result.basic,
        _col(
            [
                0.9, 0.95, 19.95, 20.47, 1.05, 0.53,
                3.95327620973974, 3.95, 4.84672379026026, 4.85,
            ],
            (2, 5),
        ),
        atol=ATOL,
        rtol=0,
    )
    np.testing.assert_allclose(
        result.student,
        _col(
            [
                0.9, 0.95, 19.95, 20.47, 1.05, 0.53,
                3.87245356151758, 3.86751165345413,
                4.75916741989827, 4.76141606796153,
            ],
            (2, 5),
        ),
        atol=ATOL,
        rtol=0,
    )
    np.testing.assert_allclose(
        result.percent,
        _col(
            [
                0.9, 0.95, 1.05, 0.53, 19.95, 20.47,
                3.80327620973974, 3.8, 4.69672379026026, 4.7,
            ],
            (2, 5),
        ),
        atol=ATOL,
        rtol=0,
    )
    np.testing.assert_allclose(
        result.bca,
        _col(
            [
                0.9, 0.95, 3.97, 2.41, 20.83, 20.93,
                3.9485274024095, 3.87235136537403, 4.7, 4.7,
            ],
            (2, 5),
        ),
        atol=ATOL,
        rtol=0,
    )


def test_grid_replicates_include_the_98_47_rank():
    result = _intervals(_grid_boot(), conf=[0.9, 0.95])
    np.testing.assert_allclose(
        result.normal,
        _col(
            [
                0.9, 0.95,
                25.553742287448266, 25.4012004147712,
                27.14625771255173, 27.298799585228796,
            ],
            (2, 3),
        ),
        atol=ATOL,
        rtol=0,
    )
    np.testing.assert_allclose(
        result.basic,
        _col(
            [
                0.9, 0.95,
                95.95, 98.47, 5.05, 2.53,
                25.55536089480626, 25.55,
                27.14463910519374, 27.15,
            ],
            (2, 5),
        ),
        atol=ATOL,
        rtol=0,
    )
    np.testing.assert_allclose(
        result.bca[:, 1:3],
        _col([3.67, 1.76, 94.18, 97.45], (2, 2)),
        atol=ATOL,
        rtol=0,
    )
    printed = print_bootci(result)
    assert "90%   (25.55, 27.15 )   (25.56, 27.14 )   (22.68, 30.02 )   " in printed
    assert "Some BCa intervals may be unstable\n" in printed


def test_log_transform_and_scale_note():
    def log(values):
        return np.log(np.asarray(values, dtype=float))

    def inverse(values):
        return np.exp(np.asarray(values, dtype=float))

    def derivative(values):
        return 1.0 / np.asarray(values, dtype=float)

    result = _intervals(
        _small_boot(),
        conf=0.95,
        type="norm",
        h=log,
        hdot=derivative,
        hinv=inverse,
    )
    np.testing.assert_allclose(
        result.normal,
        [[0.95, 3.8986422241728, 5.01790941750221]],
        atol=ATOL,
        rtol=0,
    )
    assert result.t0 == pytest.approx(4.325)
    text = print_bootci(result)
    assert "Calculations on Transformed Scale;  Intervals on Original Scale" in text
    assert "95%   ( 3.899,  5.018 )  " in text

    transformed = _intervals(_small_boot(), conf=0.95, type="perc", h=log)
    note = print_bootci(transformed)
    assert "Calculations and Intervals on  Transformed Scale" in note


def test_print_bootci_matches_the_r_layout(capsys):
    result = _intervals(
        _small_boot(), conf=[0.90, 0.95], type=["norm", "basic", "stud", "perc", "bca"]
    )
    text = print_bootci(result)
    captured = capsys.readouterr().out
    assert text == captured
    expected = (
        "Intervals : \n"
        "Level      Normal              Basic             Studentized     \n"
        "90%   ( 3.963,  4.862 )   ( 3.953,  4.847 )   ( 3.872,  4.759 )   \n"
        "95%   ( 3.877,  4.948 )   ( 3.950,  4.850 )   ( 3.868,  4.761 )  \n"
        "\n"
        "Level     Percentile            BCa          \n"
        "90%   ( 3.803,  4.697 )   ( 3.949,  4.700 )   \n"
        "95%   ( 3.800,  4.700 )   ( 3.872,  4.700 )  \n"
        "Calculations and Intervals on Original Scale\n"
        "Warning : Basic Intervals used Extreme Quantiles\n"
        "Some basic intervals may be unstable\n"
        "Warning : Studentized Intervals used Extreme Quantiles\n"
        "Some studentized intervals may be unstable\n"
        "Warning : Percentile Intervals used Extreme Quantiles\n"
        "Some percentile intervals may be unstable\n"
        "Warning : BCa Intervals used Extreme Quantiles\n"
        "Some BCa intervals may be unstable\n"
    )
    assert text[text.index("Intervals :") :] == expected


def test_delete_one_jackknife_bca_uses_one_based_indices():
    data = np.array([1.0, 2.0, 4.0, 8.0])

    def statistic(values, indices):
        return float(np.mean(values[np.asarray(indices, dtype=int) - 1]))

    boot = {
        "t0": float(np.mean(data)),
        "t": np.array([2.0, 3.0, 5.0]),
        "R": 3,
        "data": data,
        "statistic": statistic,
        "sim": "ordinary",
        "stype": "i",
        "strata": np.ones(data.size, dtype=int),
        "weights": np.full(data.size, 0.25),
        "boot_type": "boot",
    }
    result = _intervals(boot, conf=0.9, type="bca")
    np.testing.assert_allclose(result.bca, [[0.9, 0.96, 3.99, 2.0, 5.0]], atol=ATOL, rtol=0)


def test_time_series_skips_bca_and_regression_needs_influence():
    boot = _small_boot()
    boot["boot_type"] = "tsboot"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", UserWarning)
        result = boot_ci(boot, type="bca")
    assert getattr(result, "bca", None) is None
    assert any("time series" in str(item.message) for item in caught)

    short = {
        "t0": 2.0,
        "t": np.array([1.1, 1.2, 1.5, 1.7, 2.0]),
        "R": 5,
        "data": np.array([1.0, 2.0, 3.0]),
        "statistic": lambda values, indices: 0.0,
        "sim": "ordinary",
        "stype": "i",
        "strata": np.ones(3, dtype=int),
        "weights": np.full(3, 1.0 / 3.0),
        "boot_type": "boot",
    }
    with pytest.raises(ValueError, match="pass L"):
        boot_ci(short, type="bca")


def test_constant_replicates_and_length_error(capsys):
    boot = {
        "t0": 1.0,
        "t": np.ones(5),
        "R": 5,
        "data": np.arange(4.0),
        "statistic": lambda values, weights: 1.0,
        "sim": "ordinary",
        "stype": "w",
        "boot_type": "boot",
    }
    assert boot_ci(boot, type="perc") is None
    assert capsys.readouterr().out == (
        '[1] "All values of t are equal to  1 \\n Cannot calculate confidence intervals"\n'
    )
    with pytest.raises(ValueError, match="'t' must of length 5"):
        boot_ci(boot, t0=1.0, t=np.array([1.0, 2.0, 3.0]), type="perc")
    with pytest.raises(ValueError, match="supplied together"):
        boot_ci(boot, t=np.array([1.0, 2.0, 3.0, 4.0, 5.0]), type="perc")


def test_abc_ci_mean_and_stratified_difference():
    def mean_w(data, weights):
        return float(np.sum(np.asarray(data, dtype=float) * np.asarray(weights, dtype=float)))

    interval = abc_ci(np.arange(1, 9, dtype=float), mean_w, conf=[0.9, 0.95])
    np.testing.assert_allclose(
        interval,
        _col(
            [
                0.9, 0.95,
                3.1675162696113772, 2.9122477047471302,
                5.8324837303884243, 6.0877522952527201,
            ],
            (2, 3),
        ),
        atol=ATOL,
        rtol=0,
    )
    one = abc_ci(np.arange(1, 9, dtype=float), mean_w, conf=0.95)
    assert one.shape == (3,)

    values = np.array([1.0, 2.0, 3.0, 4.0, 10.0, 11.0, 12.0])

    def difference(data, weights):
        left = math.fsum(np.asarray(data[:4] * weights[:4], dtype=float))
        right = math.fsum(np.asarray(data[4:] * weights[4:], dtype=float))
        return left - right

    stratified = abc_ci(values, difference, strata=np.array([1, 1, 1, 1, 2, 2, 2]), conf=[0.9, 0.95])
    np.testing.assert_allclose(
        stratified,
        [
            [0.9, -9.70279433591194, -7.29720566941662],
            [0.95, -9.93321784974005, -7.06678215558836],
        ],
        atol=ATOL,
        rtol=0,
    )
