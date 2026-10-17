"""exp.tilt, smooth.f, tilt.boot, and control against installed boot 1.3-32."""

from __future__ import annotations

import subprocess
import textwrap

import numpy as np
import pytest

from boot.rng import set_seed
from boot.tilt import _pnorm, _qnorm, control, exp_tilt, smooth_f, tilt_boot

TOLERANCE = 1e-8


def _r(script: str) -> dict[str, np.ndarray]:
    completed = subprocess.run(
        ["Rscript", "-"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    values: dict[str, np.ndarray] = {}
    for line in completed.stdout.splitlines():
        name, _, rest = line.partition(" ")
        if not rest.strip():
            values[name] = np.array([], dtype=np.float64)
        else:
            values[name] = np.array([float(item) for item in rest.split()], dtype=np.float64)
    return values


def _boot_from_r(values, prefix, data, statistic):
    from types import SimpleNamespace

    t = values[f"{prefix}t"]
    n_stat = int(values[f"{prefix}nstat"][0])
    replicates = t.size // n_stat
    # as.numeric walks a matrix down columns: all of statistic 1, then statistic 2.
    columns = [t[i * replicates : (i + 1) * replicates] for i in range(n_stat)]
    return SimpleNamespace(
        t0=values[f"{prefix}t0"].copy(),
        t=np.column_stack(columns),
        R=int(values[f"{prefix}R"][0]),
        data=np.asarray(data, dtype=np.float64),
        strata=values[f"{prefix}strata"].copy(),
        weights=values[f"{prefix}w"].copy(),
        seed=values[f"{prefix}seed"].astype(np.int64),
        sim="ordinary",
        stype="i",
        call=SimpleNamespace(weights=None),
        boot_type="boot",
        statistic=statistic,
    )


def _mean_var(data, indices):
    values = np.asarray(data, dtype=np.float64)[np.asarray(indices, dtype=int) - 1]
    centre = float(values.mean())
    variance = float(np.sum((values - centre) ** 2) / (values.size - 1))
    return np.array([centre, variance])


def _mean(data, indices):
    values = np.asarray(data, dtype=np.float64)[np.asarray(indices, dtype=int) - 1]
    return float(values.mean())


R_REFERENCE = textwrap.dedent(
    r"""
    suppressPackageStartupMessages(library(boot))
    emit <- function(name, value) {
      cat(name, paste(sprintf("%.17g", as.numeric(value)), collapse = " "), "\n")
    }
    L <- c(-1.2, 0.3, 0.5, -0.4, 1.1, 0.2, -0.7, 0.8)
    et <- exp.tilt(L, theta = c(0.4, -0.2), t0 = 0.1)
    emit("et_p", et$p)
    emit("et_theta", et$theta)
    emit("et_lambda", et$lambda)
    et2 <- exp.tilt(L, lambda = c(0.25, -0.5), t0 = 0.1)
    emit("et2_theta", et2$theta)
    emit("et2_p", et2$p)
    et3 <- exp.tilt(L, theta = 0.5, strata = c(1, 1, 1, 1, 2, 2, 2, 2), t0 = 0)
    emit("et3_lambda", et3$lambda)
    emit("et3_p", et3$p)
    hard <- exp.tilt(c(-2, -1, 0, 1, 3), theta = 2.5, t0 = 0)
    emit("hard_lambda", hard$lambda)
    emit("hard_p", hard$p)

    set.seed(11)
    x <- c(2.3, 1.1, 4.0, 3.2, 0.7, 5.1, 2.8, 1.9)
    stat <- function(d, i) c(mean(d[i]), var(d[i]))
    b <- boot(x, stat, R = 40)
    emit("b_seed", b$seed)
    emit("b_t0", b$t0)
    emit("b_t", b$t)
    emit("b_R", b$R)
    emit("b_strata", b$strata)
    emit("b_w", b$weights)
    emit("b_nstat", 2)
    emit("smooth", smooth.f(c(2.5, 3.1), b, index = 1))
    emit("bias", control(b, index = 2, bias.adj = TRUE))
    ct <- control(b, index = 2)
    emit("ct_L", ct$L)
    emit("ct_tL", ct$tL)
    emit("ct_bias", ct$bias)
    emit("ct_var", ct$var)
    emit("ct_k3", ct$k3)

    set.seed(3)
    xs <- c(1, 2, 3, 4, 10, 11, 12, 13)
    st <- c(1, 1, 1, 1, 2, 2, 2, 2)
    b2 <- boot(xs, stat, R = 25, strata = st)
    emit("s_seed", b2$seed)
    emit("s_t0", b2$t0)
    emit("s_t", b2$t)
    emit("s_R", b2$R)
    emit("s_strata", b2$strata)
    emit("s_w", b2$weights)
    emit("s_nstat", 2)
    emit("smooth2", smooth.f(6.5, b2))
    emit("bias2", control(b2, index = 2, bias.adj = TRUE))

    set.seed(2)
    y <- c(1.2, 3.4, 2.2, 5.0, 4.1, 0.7)
    tb <- tilt.boot(y, function(d, i) mean(d[i]), R = c(20, 15), theta = 3.5)
    emit("tb_t0", tb$t0)
    emit("tb_theta", tb$theta)
    emit("tb_t", tb$t)
    emit("tb_w", tb$weights)
    emit("pnorm", pnorm(c(-2.5, -0.5, 0, 0.8, 3)))
    emit("qnorm", qnorm(c(0.001, 0.025, 0.5, 0.975, 0.999)))
    """
)


@pytest.fixture(scope="module")
def reference():
    return _r(R_REFERENCE)


def test_exp_tilt_matches_r(reference):
    L = np.array([-1.2, 0.3, 0.5, -0.4, 1.1, 0.2, -0.7, 0.8])
    tilted = exp_tilt(L, theta=[0.4, -0.2], t0=0.1)
    assert tilted.p.ravel(order="F") == pytest.approx(reference["et_p"], abs=TOLERANCE)
    assert tilted.theta == pytest.approx(reference["et_theta"], abs=TOLERANCE)
    assert tilted.lambda_ == pytest.approx(reference["et_lambda"], abs=TOLERANCE)

    from_lambda = exp_tilt(L, lambda_=[0.25, -0.5], t0=0.1)
    assert from_lambda.theta == pytest.approx(reference["et2_theta"], abs=TOLERANCE)
    assert from_lambda.p.ravel(order="F") == pytest.approx(reference["et2_p"], abs=TOLERANCE)

    stratified = exp_tilt(L, theta=0.5, strata=[1, 1, 1, 1, 2, 2, 2, 2], t0=0)
    assert stratified.lambda_ == pytest.approx(reference["et3_lambda"], abs=TOLERANCE)
    assert stratified.p == pytest.approx(reference["et3_p"], abs=TOLERANCE)

    hard = exp_tilt(np.array([-2.0, -1.0, 0.0, 1.0, 3.0]), theta=2.5)
    assert hard.lambda_ == pytest.approx(reference["hard_lambda"], abs=TOLERANCE)
    assert hard.p == pytest.approx(reference["hard_p"], abs=TOLERANCE)


def test_exp_tilt_requires_a_target():
    with pytest.raises(ValueError, match="theta"):
        exp_tilt([1.0, 2.0, 3.0])


def test_exp_tilt_rejects_an_unreachable_mean():
    with pytest.raises(ValueError, match="unable to find multiplier"):
        exp_tilt([-1.0, 0.0, 1.0], theta=50)


def test_supplied_theta_ignores_lambda():
    L = np.array([-1.2, 0.3, 0.5, -0.4, 1.1])
    from_theta = exp_tilt(L, theta=0.4, t0=0.1)
    both = exp_tilt(L, theta=0.4, lambda_=5.0, t0=0.1)
    assert both.lambda_ == pytest.approx(from_theta.lambda_, abs=TOLERANCE)
    assert both.p == pytest.approx(from_theta.p, abs=TOLERANCE)


def test_smooth_f_and_control_match_r(reference):
    data = np.array([2.3, 1.1, 4.0, 3.2, 0.7, 5.1, 2.8, 1.9])
    boot_out = _boot_from_r(reference, "b_", data, _mean_var)
    smoothed = smooth_f([2.5, 3.1], boot_out, index=1)
    assert smoothed.ravel(order="F") == pytest.approx(reference["smooth"], abs=TOLERANCE)
    assert control(boot_out, index=2, bias_adj=True) == pytest.approx(reference["bias"][0], abs=TOLERANCE)
    estimated = control(boot_out, index=2)
    assert estimated.L == pytest.approx(reference["ct_L"], abs=TOLERANCE)
    assert estimated.tL == pytest.approx(reference["ct_tL"], abs=TOLERANCE)
    assert estimated.bias == pytest.approx(reference["ct_bias"][0], abs=TOLERANCE)
    assert estimated.var == pytest.approx(reference["ct_var"][0], abs=TOLERANCE)
    assert estimated.k3 == pytest.approx(reference["ct_k3"][0], abs=TOLERANCE)


def test_stratified_smooth_and_balance(reference):
    data = np.array([1.0, 2.0, 3.0, 4.0, 10.0, 11.0, 12.0, 13.0])
    boot_out = _boot_from_r(reference, "s_", data, _mean_var)
    assert smooth_f(6.5, boot_out) == pytest.approx(reference["smooth2"], abs=TOLERANCE)
    assert control(boot_out, index=2, bias_adj=True) == pytest.approx(
        reference["bias2"][0], abs=TOLERANCE
    )


def test_control_rejects_weighted_bootstrap():
    from types import SimpleNamespace

    boot_out = SimpleNamespace(call=SimpleNamespace(weights=np.ones(3)))
    with pytest.raises(ValueError, match="weights"):
        control(boot_out)


def test_smooth_f_warns_and_keeps_the_first_column(reference):
    data = np.array([2.3, 1.1, 4.0, 3.2, 0.7, 5.1, 2.8, 1.9])
    boot_out = _boot_from_r(reference, "b_", data, _mean_var)
    matrix = np.column_stack([boot_out.t[:, 0], np.zeros(boot_out.R)])
    with pytest.warns(UserWarning, match="only first column"):
        smoothed = smooth_f([2.5, 3.1], boot_out, t=matrix)
    assert smoothed.ravel(order="F") == pytest.approx(reference["smooth"], abs=TOLERANCE)


def test_tilt_boot_matches_r(reference):
    data = np.array([1.2, 3.4, 2.2, 5.0, 4.1, 0.7])
    set_seed(2)
    result = tilt_boot(data, _mean, R=[20, 15], theta=3.5)
    assert np.asarray(result.t0, dtype=np.float64).reshape(-1) == pytest.approx(
        reference["tb_t0"], abs=TOLERANCE
    )
    assert np.asarray(result.theta, dtype=np.float64).reshape(-1) == pytest.approx(
        reference["tb_theta"], abs=TOLERANCE
    )
    assert np.asarray(result.t, dtype=np.float64).reshape(-1) == pytest.approx(
        reference["tb_t"], abs=TOLERANCE
    )
    weights = np.asarray(result.weights, dtype=np.float64)
    assert weights.ravel(order="F") == pytest.approx(reference["tb_w"], abs=TOLERANCE)


def test_tilt_boot_rejects_other_simulation_types():
    with pytest.raises(ValueError, match="sim"):
        tilt_boot([1.0, 2.0, 3.0], _mean, R=[0, 5], sim="parametric", theta=2.0)


def test_normal_cdf_and_quantile_match_r(reference):
    z = np.array([-2.5, -0.5, 0.0, 0.8, 3.0])
    probs = np.array([0.001, 0.025, 0.5, 0.975, 0.999])
    assert _pnorm(z) == pytest.approx(reference["pnorm"], abs=TOLERANCE)
    assert _qnorm(probs) == pytest.approx(reference["qnorm"], abs=TOLERANCE)
