"""tsboot against CRAN boot 1.3-32, set.seed(1), tolerance 1e-8."""

import numpy as np
import pytest

from boot.rng import sample_int, set_seed
from boot.series import _PoissonState, qnorm, tsboot

TOLERANCE = 1e-8

# qnorm values from R 4.5 qnorm after RNGkind Inversion.
_QNORM = {
    1e-8: -5.61200124417479,
    1e-6: -4.7534243088228987,
    0.001: -3.0902323061678132,
    0.01: -2.3263478740408408,
    0.025: -1.9599639845400538,
    0.05: -1.6448536269514726,
    0.1: -1.2815515655446008,
    0.25: -0.67448975019608171,
    0.5: 0.0,
    0.75: 0.67448975019608171,
    0.9: 1.2815515655446008,
    0.95: 1.6448536269514715,
    0.975: 1.9599639845400536,
    0.99: 2.3263478740408408,
    0.999: 3.0902323061678132,
    1 - 1e-8: 5.6120012433055058,
    1 / 31: -1.8485962885014084,
    30 / 31: 1.8485962885014089,
}

_FIXED = np.array(
    [
        16.333333333333332,
        9.833333333333334,
        15.166666666666666,
        14.5,
        12.0,
        15.833333333333334,
        20.333333333333332,
        13.5,
        21.0,
        18.5,
        15.166666666666666,
        16.833333333333332,
        16.333333333333332,
        17.166666666666668,
        17.5,
        12.333333333333334,
        22.166666666666668,
        10.833333333333334,
        15.333333333333334,
        12.5,
    ]
)

_GEOM = np.array(
    [
        15.366666666666667,
        17.966666666666665,
        15.3,
        15.633333333333333,
        14.766666666666667,
        14.366666666666667,
        12.633333333333333,
        9.3,
        9.966666666666667,
        18.7,
        19.1,
        15.3,
        17.0,
        16.466666666666665,
        14.433333333333334,
        20.133333333333333,
        21.3,
        12.366666666666667,
        13.1,
        12.1,
    ]
)

_MODEL = np.array(
    [
        13.2,
        15.966666666666667,
        13.3,
        17.366666666666667,
        16.5,
        15.7,
        13.333333333333334,
        14.566666666666666,
        16.733333333333334,
        13.8,
        16.433333333333334,
        14.533333333333333,
        15.733333333333333,
        14.133333333333333,
        14.466666666666667,
        16.633333333333333,
        17.6,
        15.433333333333334,
        14.266666666666667,
        16.166666666666668,
    ]
)

_SCRAMBLE = np.array(
    [
        19.519129954783999,
        15.568613748833997,
        15.294007256538514,
        18.648558181431913,
        29.256140448480501,
        26.543674248620821,
        20.867028774675067,
        22.821023665710641,
        24.27413862354274,
        23.422271429239693,
        24.343028093951943,
        19.151082684785234,
        26.133534126826259,
        15.238728408673124,
        8.742600329746864,
        8.000637569973378,
        7.3450893961051484,
        11.448814411318772,
        11.542996534813529,
        16.310230069375006,
        16.56135350677468,
        2.9000951688770513,
        8.3255083177072269,
        5.4910054541850126,
        3.4829938969000036,
        9.2402293573008301,
        9.7553969109556604,
        6.5117437074999671,
        17.662547289492643,
        20.597798432879792,
    ]
)

_SCRAMBLE_EMPIRICAL = np.array(
    [
        22, 14, 13, 16, 30, 28, 20, 23, 26, 25,
        27, 17, 29, 15, 7, 6, 5, 12, 11, 18,
        21, 1, 8, 4, 2, 9, 10, 3, 19, 24,
    ],
    dtype=float,
)


def _fresh_series_module():
    import boot.series as series

    series._POISSON = _PoissonState()


def _series():
    return np.arange(1, 31)


def test_qnorm_matches_r():
    got = np.array([qnorm(p) for p in _QNORM])
    expected = np.array(list(_QNORM.values()))
    assert np.max(np.abs(got - expected)) < TOLERANCE


def test_tsboot_fixed_mean_matches_r():
    set_seed(1)
    result = tsboot(_series(), np.mean, R=20, l=5, sim="fixed")
    assert result.t0 == pytest.approx(15.5, abs=TOLERANCE)
    assert result.R == 20
    assert result.sim == "fixed"
    assert result.l == 5
    assert result.endcorr is True
    assert result.n_sim == 30
    assert result.boot_type == "tsboot"
    assert np.max(np.abs(np.ravel(result.t) - _FIXED)) < TOLERANCE


def test_tsboot_geom_mean_matches_r():
    _fresh_series_module()
    set_seed(1)
    result = tsboot(_series(), np.mean, R=20, l=5, sim="geom", endcorr=False)
    assert result.endcorr is True
    assert result.t0 == pytest.approx(15.5, abs=TOLERANCE)
    assert np.max(np.abs(np.ravel(result.t) - _GEOM)) < TOLERANCE


def test_tsboot_model_mean_matches_r():
    def resample(tser, n_sim, args):
        index = sample_int(len(tser), n_sim, replace=True)
        return np.asarray(tser)[np.array(index) - 1]

    set_seed(1)
    result = tsboot(_series(), np.mean, R=20, sim="model", ran_gen=resample)
    assert result.t0 == pytest.approx(15.5, abs=TOLERANCE)
    assert np.max(np.abs(np.ravel(result.t) - _MODEL)) < TOLERANCE
    assert not hasattr(result, "l")
    assert result.ran_gen is resample


def test_tsboot_scramble_matches_r():
    set_seed(1)
    normal = tsboot(_series(), lambda z: np.asarray(z, dtype=float), R=1, sim="scramble")
    assert normal.norm is True
    assert np.max(np.abs(np.ravel(normal.t) - _SCRAMBLE)) < TOLERANCE
    set_seed(1)
    empirical = tsboot(
        _series(),
        lambda z: np.asarray(z, dtype=float),
        R=1,
        sim="scramble",
        norm=False,
    )
    assert np.max(np.abs(np.ravel(empirical.t) - _SCRAMBLE_EMPIRICAL)) < TOLERANCE


def test_tsboot_endcorr_false_and_matrix():
    set_seed(1)
    shortened = tsboot(_series(), np.mean, R=5, l=5, sim="fixed", endcorr=False)
    expected = np.array(
        [16.833333333333332, 11.333333333333334, 12.0, 14.166666666666666, 18.166666666666668]
    )
    assert shortened.endcorr is False
    assert np.max(np.abs(np.ravel(shortened.t) - expected)) < TOLERANCE

    set_seed(1)
    matrix = np.column_stack([np.arange(1, 13), 2 * np.arange(1, 13)])
    both = tsboot(matrix, lambda z: (np.mean(z[:, 0]), np.mean(z[:, 1])), R=3, l=4, sim="fixed")
    expected_matrix = np.array(
        [
            [6.5, 13.0],
            [4.166666666666667, 8.333333333333334],
            [7.833333333333333, 15.666666666666666],
        ]
    )
    assert np.max(np.abs(both.t - expected_matrix)) < TOLERANCE


def test_tsboot_rejects_bad_arguments():
    series = _series()
    with pytest.raises(ValueError, match="positive"):
        tsboot(series, np.mean, R=0, l=5, sim="fixed")
    with pytest.raises(ValueError, match="invalid value of 'l'"):
        tsboot(series, np.mean, R=2, sim="fixed")
    with pytest.raises(ValueError, match="unrecognized value of 'sim'"):
        tsboot(series, np.mean, R=2, l=5, sim="nope")
    matrix = np.column_stack([series[:12], series[:12]])
    with pytest.raises(ValueError, match="multivariate"):
        tsboot(matrix, np.mean, R=1, sim="scramble")
