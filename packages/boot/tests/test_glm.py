"""glm.diag, glm.diag.plots, and cv.glm against boot 1.3-32."""

from __future__ import annotations

import subprocess
import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from boot.glm import cv_glm, glm, glm_diag, glm_diag_plots
from boot.rng import set_seed

TOLERANCE = 1e-8

BODY = np.array(
    [
        3.385, 0.48, 1.35, 465, 36.33, 27.66, 14.83, 1.04, 4.19, 0.425, 0.101,
        0.92, 1, 0.005, 0.06, 3.5, 2, 1.7, 2547, 0.023, 187.1, 521, 0.785, 10,
        3.3, 0.2, 1.41, 529, 207, 85, 0.75, 62, 6654, 3.5, 6.8, 35, 4.05, 0.12,
        0.023, 0.01, 1.4, 250, 2.5, 55.5, 100, 52.16, 10.55, 0.55, 60, 3.6,
        4.288, 0.28, 0.075, 0.122, 0.048, 192, 3, 160, 0.9, 1.62, 0.104, 4.235,
    ]
)
BRAIN = np.array(
    [
        44.5, 15.5, 8.1, 423, 119.5, 115, 98.2, 5.5, 58, 6.4, 4, 5.7, 6.6, 0.14,
        1, 10.8, 12.3, 6.3, 4603, 0.3, 419, 655, 3.5, 115, 25.6, 5, 17.5, 680,
        406, 325, 12.3, 1320, 5712, 3.9, 179, 56, 17, 1, 0.4, 0.25, 12.5, 490,
        12.1, 175, 157, 440, 179.5, 2.4, 81, 21, 39.2, 1.9, 1.2, 3, 0.33, 180,
        25, 169, 2.6, 11.4, 2.5, 50.4,
    ]
)
NODAL_R = np.array(
    [
        1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1,
        1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1,
        0, 1, 1, 0, 0,
    ],
    dtype=float,
)
NODAL_STAGE = np.array(
    [
        1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0,
        0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0,
        0, 1, 1, 1, 0, 0, 0,
    ],
    dtype=float,
)
NODAL_XRAY = np.array(
    [
        1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0,
        1, 0, 1, 1,
    ],
    dtype=float,
)
NODAL_ACID = np.array(
    [
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0,
        0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0,
        0, 0, 0, 1, 1, 0,
    ],
    dtype=float,
)


def mammals():
    return {"body": BODY.copy(), "brain": BRAIN.copy()}


def nodal():
    return {
        "r": NODAL_R.copy(),
        "stage": NODAL_STAGE.copy(),
        "xray": NODAL_XRAY.copy(),
        "acid": NODAL_ACID.copy(),
    }


def misclass(y, yhat):
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(yhat)) > 0.5))


def _r_reference() -> dict[str, np.ndarray]:
    script = r"""
library(boot)
suppressPackageStartupMessages(library(MASS))
dumpv <- function(name, x) {
  cat("BEGIN ", name, " ", length(as.numeric(x)), "\n", sep = "")
  cat(sprintf("%.17g", as.numeric(x)), sep = "\n")
  cat("END\n")
}
mammals.glm <- glm(log(brain) ~ log(body), data = mammals)
nodal.glm <- glm(r ~ stage + xray + acid, binomial, data = nodal)
gd <- glm.diag(mammals.glm)
bd <- glm.diag(nodal.glm)
for (nm in names(gd)) dumpv(paste0("g_", nm), gd[[nm]])
for (nm in names(bd)) dumpv(paste0("b_", nm), bd[[nm]])
dumpv("gcoef", coef(mammals.glm))
dumpv("bcoef", coef(nodal.glm))
set.seed(1)
dumpv("loo", cv.glm(mammals, mammals.glm)$delta)
set.seed(1)
dumpv("k6", cv.glm(mammals, mammals.glm, K = 6)$delta)
set.seed(1)
n <- nrow(mammals); K <- 6L; f <- ceiling(n/K)
dumpv("split6", boot:::sample0(rep(1L:K, f), n))
cost <- function(r, pi = 0) mean(abs(r - pi) > 0.5)
set.seed(1)
dumpv("nloo", cv.glm(nodal, nodal.glm, cost, K = nrow(nodal))$delta)
set.seed(1)
dumpv("k11", cv.glm(nodal, nodal.glm, cost, K = 11)$delta)
set.seed(1)
n <- nrow(nodal); K <- 11L; f <- ceiling(n/K)
dumpv("split11", boot:::sample0(rep(1L:K, f), n))
y2 <- gd$rd
dumpv("x2", qnorm(ppoints(length(y2)))[rank(y2)])
dumpv("x1", predict(mammals.glm))
dumpv("hh", gd$h / (1 - gd$h))
y2b <- bd$rd
dumpv("bx2", qnorm(ppoints(length(y2b)))[rank(y2b)])
dumpv("qnorm", qnorm(c(0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)))
dumpv("zero_h", glm.diag(glm(c(1,2,4,3) ~ c(1,2,3,4), weights = c(1,1,0,1)))$h)
"""
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed: dict[str, np.ndarray] = {}
    name = None
    values: list[float] = []
    for line in completed.stdout.splitlines():
        if line.startswith("BEGIN "):
            name = line.split()[1]
            values = []
        elif line == "END" and name is not None:
            parsed[name] = np.array(values, dtype=np.float64)
            name = None
        elif name is not None and line:
            values.append(float(line))
    return parsed


@pytest.fixture(scope="module")
def reference():
    return _r_reference()


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def test_gaussian_and_binomial_diagnostics_match_glm_diag(reference):
    gaussian = glm_diag(glm("log(brain) ~ log(body)", mammals()))
    binomial = glm_diag(glm("r ~ stage + xray + acid", nodal(), family="binomial"))
    for key in ("res", "rd", "rp", "cook", "h", "sd"):
        assert gaussian[key] == pytest.approx(reference[f"g_{key}"], abs=TOLERANCE)
        assert binomial[key] == pytest.approx(reference[f"b_{key}"], abs=TOLERANCE)
    assert gaussian["sd"] == pytest.approx(0.69429473114161744, abs=TOLERANCE)
    assert binomial["sd"] == 1.0
    fit_g = glm("log(brain) ~ log(body)", mammals())
    fit_b = glm("r ~ stage + xray + acid", nodal(), family="binomial")
    assert fit_g.coefficients == pytest.approx(reference["gcoef"], abs=TOLERANCE)
    assert fit_b.coefficients == pytest.approx(reference["bcoef"], abs=TOLERANCE)
    # The manual's leave-one-out shortcut for the gaussian linear model.
    shortcut = np.mean((fit_g.y - fit_g.fitted_values) ** 2 / (1.0 - gaussian["h"]) ** 2)
    assert shortcut == pytest.approx(reference["loo"][0], abs=TOLERANCE)


def test_plot_coordinates_match_the_manual_panels(reference):
    gaussian = glm("log(brain) ~ log(body)", mammals())
    diag = glm_diag_plots(gaussian, ret=True)
    axes = plt.gcf().axes
    assert axes[0].lines[0].get_xdata() == pytest.approx(reference["x1"], abs=TOLERANCE)
    assert axes[0].lines[0].get_ydata() == pytest.approx(reference["g_res"], abs=TOLERANCE)
    assert axes[0].get_xlabel() == "Linear predictor"
    assert axes[0].get_ylabel() == "Residuals"
    assert axes[1].lines[0].get_xdata() == pytest.approx(reference["x2"], abs=TOLERANCE)
    assert axes[1].lines[0].get_ydata() == pytest.approx(diag["rd"], abs=TOLERANCE)
    assert axes[1].get_xlabel() == "Ordered deviance residuals"
    assert axes[1].get_ylabel() == "Quantiles of standard normal"
    diagonal = axes[1].lines[1].get_xydata()
    assert diagonal[1, 1] - diagonal[0, 1] == pytest.approx(diagonal[1, 0] - diagonal[0, 0], abs=TOLERANCE)
    assert axes[2].lines[0].get_xdata() == pytest.approx(reference["hh"], abs=TOLERANCE)
    assert axes[2].lines[0].get_ydata() == pytest.approx(reference["g_cook"], abs=TOLERANCE)
    # cooky sits above every Cook statistic, so only the leverage line is drawn.
    assert len(axes[2].lines) == 2
    assert len(axes[3].lines) == 1
    assert axes[3].lines[0].get_xdata() == pytest.approx(np.arange(1, 63), abs=0.0)
    assert diag["h"] == pytest.approx(reference["g_h"], abs=TOLERANCE)

    plt.close("all")
    binomial = glm("r ~ stage + xray + acid", nodal(), family="binomial")
    glm_diag_plots(binomial)
    drawn = plt.gcf().axes[1].lines[0].get_xdata()
    assert drawn == pytest.approx(reference["bx2"], abs=TOLERANCE)


def test_cv_glm_matches_seeded_folds(reference):
    from boot.glm import _folds

    gaussian = glm("log(brain) ~ log(body)", mammals())
    binomial = glm("r ~ stage + xray + acid", nodal(), family="binomial")
    set_seed(1)
    assert _folds(62, 6) == pytest.approx(reference["split6"], abs=0.0)
    set_seed(1)
    leave = cv_glm(mammals(), gaussian)
    assert leave["K"] == 62
    assert leave["delta"] == pytest.approx(reference["loo"], abs=TOLERANCE)
    set_seed(1)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        six = cv_glm(mammals(), gaussian, K=6)
    assert six["K"] == 6
    assert six["delta"] == pytest.approx(
        [0.48223969146504098, 0.48071820312449393], abs=TOLERANCE
    )
    assert six["delta"] == pytest.approx(reference["k6"], abs=TOLERANCE)
    set_seed(1)
    assert _folds(53, 11) == pytest.approx(reference["split11"], abs=0.0)
    set_seed(1)
    nodal_leave = cv_glm(nodal(), binomial, cost=misclass)
    assert nodal_leave["delta"] == pytest.approx(reference["nloo"], abs=TOLERANCE)
    set_seed(1)
    eleven = cv_glm(nodal(), binomial, cost=misclass, K=11)
    assert eleven["K"] == 11
    assert eleven["delta"] == pytest.approx(reference["k11"], abs=TOLERANCE)


def test_zero_weight_leverage_is_zero(reference):
    fit = glm("y ~ x", {"y": [1.0, 2, 4, 3], "x": [1.0, 2, 3, 4]}, weights=[1, 1, 0, 1])
    diag = glm_diag(fit)
    assert diag["h"] == pytest.approx(reference["zero_h"], abs=TOLERANCE)
    assert diag["h"][2] == 0.0
    assert fit.df_residual == 1


def test_k_outside_range_and_k_adjustment():
    from boot.glm import _adjust_k

    with pytest.raises(ValueError, match="outside allowable range"):
        _adjust_k(10, 1)
    with pytest.raises(ValueError, match="outside allowable range"):
        _adjust_k(10, 11)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert _adjust_k(10, 4) == 5
    assert any("5.000000" in str(item.message) for item in caught)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert _adjust_k(62, 6) == 6
    assert caught == []


def test_qnorm_matches_r(reference):
    from boot.glm import _qnorm

    got = _qnorm([0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
    assert got == pytest.approx(reference["qnorm"], abs=TOLERANCE)


def test_iden_is_refused_and_negative_subset_renumbers_cases():
    fit = glm("log(brain) ~ log(body)", mammals())
    with pytest.raises(ValueError, match="identify"):
        glm_diag_plots(fit, iden=True)
    glm_diag_plots(fit, subset=[-1])
    cases = plt.gcf().axes[3].lines[0].get_xdata()
    assert cases[0] == 2
    assert cases[-1] == 63
    assert len(cases) == 62


def test_no_intercept_term():
    fit = glm("y ~ x - 1", {"y": [1.0, 2.0, 3.0], "x": [1.0, 2.0, 3.0]})
    assert fit.coefficients.shape == (1,)
    assert fit.coefficients[0] == pytest.approx(1.0, abs=TOLERANCE)
