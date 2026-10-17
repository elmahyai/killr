"""Empirical influence, linear approximation, and envelopes against boot 1.3-32."""

import warnings
from types import SimpleNamespace

import numpy as np
import pytest

from boot.influence import empinf, envelope, linear_approx
from boot.rng import set_seed, unif


def mean_w(d, w):
    d = np.asarray(d, dtype=float)
    w = np.asarray(w, dtype=float)
    return np.sum(d * w) / np.sum(w)


def var_w(d, w):
    d = np.asarray(d, dtype=float)
    w = np.asarray(w, dtype=float)
    n = d.size
    mean = np.sum(d * w)
    return n / (n - 1.0) * np.sum(w * (d - mean) ** 2)


def mean_f(d, f):
    d = np.asarray(d, dtype=float)
    f = np.asarray(f, dtype=float)
    return np.sum(d * f) / np.sum(f)


def mean_i(d, i):
    d = np.asarray(d, dtype=float)
    return float(np.mean(d[np.asarray(i, dtype=int) - 1]))


X = np.array([2.2, 1.1, 4.4, 3.0, 5.5, 0.2, 6.1, 7.3])
STRATA = np.array([1, 1, 1, 1, 2, 2, 2, 2])

# sprintf("%.17g") from R 4.5 boot 1.3-32
MEAN_R = np.array(
    [
        -1.5250000000008868,
        -2.6250000000018758,
        0.67499999999753868,
        -0.72500000000275122,
        1.7749999999985278,
        -3.525000000003331,
        2.3749999999971294,
        3.5749999999978854,
    ]
)
VAR_R = np.array(
    [
        -3.6560465178681056,
        1.5604441964214288,
        -5.7929222321533302,
        -5.7129322321571863,
        -2.7133072321561258,
        7.8853677678409895,
        0.13205133927840507,
        8.2910313392758894,
    ]
)
LIN_R = np.array(
    [
        2.412499999998174,
        4.0749999999974076,
        3.7124999999973647,
        3.5499999999977434,
        4.9499999999975888,
        3.6999999999978379,
        3.5999999999976269,
        3.5124999999978308,
        2.5499999999974095,
        2.4624999999980575,
        2.7374999999978606,
        3.4999999999974158,
        3.7374999999981946,
        3.9624999999976702,
        2.9874999999981662,
        5.0249999999978581,
        2.5374999999974386,
        2.9374999999973945,
        4.1624999999980918,
        4.0749999999978517,
        3.0749999999975182,
        4.924999999997647,
        5.4999999999976392,
        3.6499999999979544,
        2.7499999999987197,
        2.8124999999976859,
        3.2749999999974961,
        4.2999999999977714,
        2.8249999999981008,
        3.2374999999975835,
    ]
)


def _boot(data, statistic, replicates, seed, strata=None, stype="w", sim="ordinary", t0=None, t=None):
    if t0 is None:
        if strata is None:
            weights = np.full(len(np.asarray(data)), 1.0 / len(np.asarray(data)))
        else:
            from boot.influence import _group_codes

            codes = _group_codes(strata, len(np.asarray(data)))
            weights = 1.0 / np.bincount(codes)[codes]
        if stype == "w":
            t0 = np.array([statistic(data, weights)])
        elif stype == "i":
            t0 = np.array([statistic(data, np.arange(1, len(np.asarray(data)) + 1))])
        else:
            t0 = np.array([statistic(data, np.ones(len(np.asarray(data))))])
    return SimpleNamespace(
        data=data,
        statistic=statistic,
        stype=stype,
        sim=sim,
        strata=strata,
        R=replicates,
        seed=seed,
        t0=np.asarray(t0, dtype=float),
        t=t,
    )


def test_infinitesimal_jackknife_of_mean_and_variance_matches_r():
    assert np.max(np.abs(empinf(data=X, statistic=mean_w) - MEAN_R)) < 1e-8
    assert np.max(np.abs(empinf(data=X, statistic=var_w) - VAR_R)) < 1e-8


def test_jackknife_and_positive_jackknife_match_r():
    jack = np.array(
        [
            -3.27602040816325,
            2.68642857142858,
            -5.71846938775509,
            -5.62704081632652,
            -2.19846938775509,
            9.91581632653062,
            1.05377551020409,
            10.3794897959184,
        ]
    )
    positive = np.array(
        [
            -3.95103174603176,
            0.686428571428555,
            -5.8507142857143,
            -5.77960317460319,
            -3.11293650793652,
            6.30928571428569,
            -0.583412698412706,
            6.66992063492062,
        ]
    )
    assert np.max(np.abs(empinf(data=X, statistic=var_w, type="jack") - jack)) < 1e-8
    assert np.max(np.abs(empinf(data=X, statistic=var_w, type="pos") - positive)) < 1e-8


def test_stratified_weights_frequencies_and_indices_match_r():
    stratified = np.array(
        [
            -0.237500000000779,
            -0.787500000001273,
            0.86250000000021,
            0.162499999998289,
            0.362499999997823,
            -2.28750000000133,
            0.662500000000676,
            1.26249999999928,
        ]
    )
    assert np.max(np.abs(empinf(data=X, statistic=mean_w, strata=STRATA) - stratified)) < 1e-8
    labels = ["b", "b", "b", "b", "a", "a", "a", "a"]
    assert np.max(np.abs(empinf(data=X, statistic=mean_w, strata=labels) - stratified)) < 1e-8
    jack_f = np.array(
        [
            -0.653571428571429,
            -1.125,
            0.289285714285715,
            -0.310714285714286,
            0.760714285714286,
            -1.51071428571429,
            1.01785714285714,
            1.53214285714286,
        ]
    )
    positive_i = np.array(
        [
            -0.847222222222221,
            -1.45833333333333,
            0.375,
            -0.402777777777779,
            0.98611111111111,
            -1.95833333333333,
            1.31944444444444,
            1.98611111111111,
        ]
    )
    got_f = empinf(data=X, statistic=mean_f, type="jack", stype="f", strata=STRATA)
    got_i = empinf(data=X, statistic=mean_i, type="pos", stype="i", strata=STRATA)
    assert np.max(np.abs(got_f - jack_f)) < 1e-8
    assert np.max(np.abs(got_i - positive_i)) < 1e-8


def test_second_component_and_extra_arguments():
    def two(d, w, scale=1.0):
        d = np.asarray(d, dtype=float)
        w = np.asarray(w, dtype=float)
        return np.array([scale * np.sum(d * w) / np.sum(w), np.sum((d**2) * w) / np.sum(w)])

    second = np.array(
        [
            -14.5599999999888,
            -18.1900000000041,
            -0.0400000000126965,
            -10.4000000000042,
            10.8500000000049,
            -19.360000000006,
            17.8099999999972,
            33.8899999999853,
        ]
    )
    assert np.max(np.abs(empinf(data=X, statistic=two, index=2) - second)) < 1e-8
    scaled = empinf(data=X, statistic=two, scale=2.0)
    assert np.max(np.abs(scaled - 2.0 * empinf(data=X, statistic=mean_w))) < 1e-8


def test_regression_influence_matches_r_glm():
    boot = _boot(X, mean_w, 30, seed=1)
    from boot.influence import _boot_array

    frequencies = _boot_array(boot)
    replicates = np.array([mean_w(X, frequencies[row] / len(X)) for row in range(30)])
    boot.t = replicates.reshape(-1, 1)
    expected = np.array([-1.525, -2.625, 0.675, -0.725, 1.775, -3.525, 2.375, 3.575])
    assert np.max(np.abs(empinf(boot, type="reg") - expected)) < 1e-8
    held = replicates.copy()
    held[2] = np.inf
    without = empinf(boot, type="reg", t=held)
    assert np.max(np.abs(without - expected)) < 1e-8
    assert np.all(np.isfinite(without))


def test_linear_approx_matches_r_and_restores_the_generator():
    boot = _boot(X, mean_w, 30, seed=1)
    assert np.max(np.abs(linear_approx(boot) - LIN_R)) < 1e-8
    supplied = linear_approx(boot, L=empinf(data=X, statistic=mean_w), t0=float(np.mean(X)))
    assert np.max(np.abs(supplied - LIN_R)) < 1e-8
    set_seed(1)
    before = unif()
    set_seed(1)
    linear_approx(boot)
    after = unif()
    assert before == after


def test_seed_vector_matches_set_seed():
    from boot import rng

    set_seed(1)
    signed = [10403, rng._mti] + [value if value < 2**31 else value - 2**32 for value in rng._mt]
    boot = _boot(X, mean_w, 30, seed=signed)
    set_seed(99)
    assert np.max(np.abs(linear_approx(boot) - LIN_R)) < 1e-8


def test_t0_without_t_or_l_is_subscripted_not_replaced():
    boot = _boot(X, mean_w, 30, seed=1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        got = linear_approx(boot, t0=999)
    assert any("neither 't' nor 'L'" in str(item.message) for item in caught)
    # Installed linear.approx keeps t0[index]. 999 - mean(X) is the shift from LIN_R.
    assert np.max(np.abs(got - (LIN_R + (999.0 - 3.725)))) < 1e-8


def test_city_ratio_matches_r():
    city = {
        "u": np.array([138, 93, 61, 179, 48, 37, 29, 23, 30, 2], dtype=float),
        "x": np.array([143, 104, 69, 260, 75, 63, 50, 48, 111, 50], dtype=float),
    }

    def ratio(d, w):
        return np.sum(d["x"] * w) / np.sum(d["u"] * w)

    expected = np.array(
        [
            -1.0436781528389,
            -0.584177631015592,
            -0.37092459027388,
            -0.189589956496317,
            0.0316414160339562,
            0.105448784555318,
            0.0923634495619829,
            0.203650741685824,
            1.02178279783427,
            0.733811322344291,
        ]
    )
    assert np.max(np.abs(empinf(data=city, statistic=ratio) - expected)) < 1e-8


def test_envelope_order_statistics_and_search():
    abscissa = np.arange(1, 81)[:, None]
    grid = np.arange(1, 6)[None, :]
    mat = (abscissa * grid) % 17 + grid
    env = envelope(mat=mat, level=[0.8, 0.95])
    assert np.array_equal(env.k_pt, [8, 73])
    assert np.array_equal(env.k_ov, [2, 79])
    assert np.allclose(env.err_pt, [0.19753086419753085, 0.8148148148148148])
    assert np.allclose(env.err_ov, [0.04938271604938271, 0.0])
    assert np.allclose(env.err_nom, [0.2, 0.05])
    assert np.array_equal(env.point, np.array([[16, 17, 18, 19, 20], [2, 3, 4, 5, 6]]))
    assert np.array_equal(env.overall, np.array([[17, 18, 19, 20, 21], [1, 2, 3, 4, 5]]))


def test_envelope_warning_and_tied_ranks():
    rows = np.arange(1, 51)[:, None]
    cols = np.arange(1, 7)[None, :]
    mat = ((rows + 3 * cols) % 13) + rows
    with pytest.warns(UserWarning, match="unable to achieve requested overall error rate"):
        env = envelope(mat=mat, level=0.9)
    assert np.array_equal(env.k_pt, [2, 49])
    assert np.array_equal(env.k_ov, [1, 50])
    assert np.allclose(env.point[:, :3], np.array([[58, 55, 55], [7, 8, 6]]))
    assert np.allclose(env.overall[:, :3], np.array([[60, 57, 57], [5, 7, 4]]))

    # sample(1:5, 120, replace=TRUE) under set.seed(4), stored column-major
    drawn = np.array(
        [
            3, 3, 3, 4, 3, 5, 2, 3, 2, 1, 4, 3, 3, 3, 5, 5, 5, 2, 4, 5,
            5, 5, 1, 3, 5, 4, 1, 4, 3, 5, 4, 4, 4, 5, 5, 5, 1, 2, 2, 4,
            2, 2, 2, 3, 3, 3, 2, 5, 1, 4, 2, 4, 3, 1, 5, 5, 4, 2, 1, 1, 4,
            1, 4, 4, 4, 5, 5, 2, 5, 5, 3, 2, 4, 2, 5, 1, 3, 1, 3, 2, 1,
            5, 3, 5, 1, 3, 4, 4, 4, 4, 1, 3, 3, 1, 5, 2, 1, 1, 3, 3, 1,
            4, 1, 5, 4, 1, 2, 1, 1, 2, 3, 2, 2, 5, 3, 5, 2, 2, 3, 5,
        ]
    )
    tied = drawn.reshape((40, 3), order="F")
    tied_env = envelope(mat=tied, level=[0.8, 0.9])
    assert np.array_equal(tied_env.k_pt, [4, 37])
    assert np.array_equal(tied_env.k_ov, [3, 38])
    assert np.allclose(tied_env.err_pt, [8 / 41, 0.414634146341463])
    assert np.allclose(tied_env.err_ov, [6 / 41, 4 / 41])
    assert np.array_equal(tied_env.point, np.array([[5, 5, 5], [1, 1, 1]]))
    assert np.array_equal(tied_env.overall, np.array([[5, 5, 5], [1, 1, 1]]))


def test_errors_and_index_warning():
    with pytest.raises(ValueError, match="neither 'data'"):
        empinf(statistic=mean_w)
    with pytest.raises(ValueError, match="bootstrap object needed"):
        empinf(data=X, statistic=mean_w, type="reg")
    with pytest.raises(ValueError, match="parametric"):
        empinf(boot_out=SimpleNamespace(sim="parametric", data=X), type="jack")
    with pytest.raises(ValueError, match='type="inf"'):
        empinf(data=X, statistic=mean_f, stype="f", type="inf")
    with pytest.warns(UserWarning, match="only first element"):
        got = empinf(data=X, statistic=mean_w, index=[1, 2])
    assert np.max(np.abs(got - MEAN_R)) < 1e-8
    with pytest.raises(ValueError, match="scalar"):
        envelope(mat=np.ones((10, 1)))
    with pytest.warns(UserWarning, match="unable to achieve requested overall error rate"):
        with pytest.raises(ValueError, match="partial"):
            envelope(mat=np.arange(120, dtype=float).reshape(30, 4), level=0.95)


def test_stratified_frequency_array_matches_boot_array():
    from boot.influence import _boot_array

    boot = _boot(X, mean_w, 40, seed=2, strata=STRATA)
    expected = np.array(
        [
            [2, 0, 1, 1, 1, 0, 2, 1],
            [2, 0, 1, 1, 1, 3, 0, 0],
            [1, 2, 1, 0, 0, 1, 2, 1],
            [0, 1, 1, 2, 1, 2, 0, 1],
            [1, 2, 0, 1, 3, 0, 0, 1],
        ],
        dtype=float,
    )
    assert np.array_equal(_boot_array(boot)[:5], expected)
