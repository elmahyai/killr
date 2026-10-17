import numpy as np

from boot.rng import set_seed
from quantreg import (
    bandwidth_rq,
    combos,
    critval,
    curv,
    dither,
    kselect,
    kuantile,
    q489,
    rq_fit_br,
    sfn_message,
    srisk,
)


def test_bandwidth_matches_the_recorded_r_value():
    assert abs(bandwidth_rq(0.5, 100) - 0.20931604694700326) < 1e-8
    assert abs(bandwidth_rq(0.9, 50, hs=False, alpha=0.1) - 0.085801869123129884) < 1e-8


def test_order_statistics_and_combinations():
    x = [3, 1, 4, 1, 5, 9, 2, 6]
    assert np.allclose(kselect(x, [1, 3, 8]), [1, 2, 9])
    assert q489(x, 0.5) == 3
    assert np.allclose(kuantile(x, [0.25, 0.5, 0.75])["y"], [1.75, 3.5, 5.25])
    columns = combos(5, 2)
    assert columns.shape == (2, 10)
    assert columns[:, 0].tolist() == [1, 2]
    assert columns[:, 1].tolist() == [1, 5]


def test_critval_is_the_uniroot_value():
    assert abs(critval(1) - 2.248121524196371) < 1e-8


def test_dither_repeats_rs_first_draw():
    set_seed(2)
    jitter = dither([1, 1, 2, 4])
    assert np.allclose(
        jitter,
        [0.68488225992769003, 1.2023740359582007, 2.0733263348229229, 3.6680519203655422],
    )


def test_point_estimate_and_sigma_risk():
    design = np.loadtxt("/tmp/qrdat.txt")
    fit = rq_fit_br(design[:, :3], design[:, 3], tau=0.5)
    assert np.allclose(
        fit["coefficients"],
        [0.77773485175047, 2.2522921359209, -0.866409933124404],
        atol=1e-8,
    )
    returns = np.array(
        [[0.02, 0.01, -0.01], [0.03, 0.0, 0.02], [-0.02, 0.04, 0.01], [0.01, -0.01, 0.02]]
    )
    risk = srisk(returns, mu=0.01, lambda_=1e6)
    assert abs(risk["muhat"] - 0.01) < 1e-8
    assert abs(risk["sigma"] - 0.0045749571099781396) < 1e-8


def test_messages_and_censoring_side():
    assert sfn_message(1).startswith("insufficient storage")
    paired = curv([3, 4], [1, 2])
    assert paired["ctype"] == "left"
    assert paired["time"].tolist() == [3, 4]
