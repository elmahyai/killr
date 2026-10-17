import math

import numpy as np

from nloptr import bobyqa, crs2lm, is_nloptr, nl_grad, nl_opts, nloptr


def test_rosenbrock_lbfgs_matches_r():
    def eval_f(x):
        return 100 * (x[1] - x[0] * x[0]) ** 2 + (1 - x[0]) ** 2

    def eval_grad_f(x):
        return np.array(
            [
                -400 * x[0] * (x[1] - x[0] * x[0]) - 2 * (1 - x[0]),
                200 * (x[1] - x[0] * x[0]),
            ]
        )

    result = nloptr(
        [-1.2, 1],
        eval_f,
        eval_grad_f,
        opts={"algorithm": "NLOPT_LD_LBFGS", "xtol_rel": 1e-8},
    )
    assert result.status == 1
    assert result.iterations == 56
    assert result.solution[0] == 0.9999999999928465
    assert result.solution[1] == 0.99999999998521971
    assert result.objective == 7.3572722689780245e-23


def test_gradient_is_within_tolerance():
    gradient = nl_grad(np.array([0, 0.2, 0.4, 0.6, 0.8, 1.0]), lambda x: np.sum(x**2))
    expected = np.array([0.0, 0.4, 0.8, 1.2, 1.6, 2.0])
    assert np.max(np.abs(gradient - expected)) < 1e-8


def test_is_nloptr_rejects_null():
    assert is_nloptr(None) is False


def test_nl_opts_clears_algorithm():
    opts = nl_opts({"xtol_rel": 1e-8, "maxeval": 2000, "algorithm": "NLOPT_LD_LBFGS"})
    assert opts["algorithm"] is None
    assert opts["maxeval"] == 2000
    assert math.isclose(opts["xtol_rel"], 1e-8)


def test_seeded_crs_matches_r():
    def rbf(x):
        return (1 - x[0]) ** 2 + 100 * (x[1] - x[0] ** 2) ** 2

    result = crs2lm(
        np.zeros(2),
        rbf,
        lower=np.full(2, -3.0),
        upper=np.full(2, 3.0),
        ranseed=10,
        maxeval=200,
        xtol_rel=1e-6,
    )
    assert result["par"][0] == 0.77556610216855693
    assert result["par"][1] == 0.58163038716434035
    assert result["convergence"] == 5


def test_bobyqa_start():
    def rbf(x):
        return (1 - x[0]) ** 2 + 100 * (x[1] - x[0] ** 2) ** 2

    result = bobyqa([0, 0], rbf)
    assert result["convergence"] == 4
    assert abs(result["par"][0] - 1) < 1e-6
