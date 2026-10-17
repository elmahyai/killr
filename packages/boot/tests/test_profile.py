"""Checks for the boot profile practicals against installed boot 1.3-32."""

from __future__ import annotations

import math
import shutil
import subprocess

import numpy as np
import pytest

from boot.profile import eef_profile, el_profile, lik_ci, nested_corr
from boot.profile import _corr_fun

TOLERANCE = 1e-8
GRAV7 = np.array(
    [76, 79, 81, 79, 77, 79, 79, 78, 79, 82, 76, 73, 64],
    dtype=np.float64,
)
AIR = np.array(
    [3, 5, 7, 18, 43, 85, 91, 98, 100, 130, 230, 487],
    dtype=np.float64,
)

_R_PROFILES = r"""
suppressPackageStartupMessages(library(boot))
EL.fixed <- function(y, tmin = min(y) + 0.1, tmax = max(y) - 0.1, n.t = 25,
                     u = function(y, t) y - t) {
  EL.loglik <- function(lambda) {
    temp <- 1 + lambda * EL.stuff$u
    if (any(!is.finite(temp) | temp <= 0)) NA_real_ else -sum(log(temp))
  }
  EL.paras <- matrix(NA_real_, n.t, 3)
  lam <- 0.001
  for (it in 0:(n.t - 1)) {
    t <- tmin + ((tmax - tmin) * it) / (n.t - 1)
    EL.stuff <- list(u = as.vector(u(y, t)))
    EL.out <- suppressWarnings(nlm(EL.loglik, lam))
    i <- 1
    while (EL.out$code > 2 && (i < 20)) {
      i <- i + 1
      lam <- lam / 5
      EL.out <- suppressWarnings(nlm(EL.loglik, lam))
    }
    EL.paras[1 + it, ] <- c(t, EL.loglik(EL.out$estimate), EL.out$estimate)
    lam <- EL.out$estimate
  }
  EL.paras[, 2] <- EL.paras[, 2] - max(EL.paras[, 2])
  EL.paras
}
EEF.fixed <- function(y, tmin = min(y) + 0.1, tmax = max(y) - 0.1, n.t = 25,
                      u = function(y, t) y - t) {
  EEF.paras <- matrix(NA_real_, n.t + 1, 4)
  for (it in 0:n.t) {
    t <- tmin + (tmax - tmin) * it / n.t
    psi <- as.vector(u(y, t))
    zero <- rep(0, length(psi))
    fit <- suppressWarnings(glm(zero ~ psi - 1, poisson(log)))
    f <- fitted(fit)
    EEF.paras[1 + it, ] <- c(t, sum(log(f) - log(sum(f))), sum(f - 1), coefficients(fit))
  }
  EEF.paras[, 2] <- EEF.paras[, 2] - max(EEF.paras[, 2])
  EEF.paras[, 3] <- EEF.paras[, 3] - max(EEF.paras[, 3])
  EEF.paras
}
emit <- function(name, mat) {
  cat(name, "\n", sep = "")
  cat(paste(sprintf("%.17g", as.vector(t(mat))), collapse = " "), "\n", sep = "")
}
grav <- c(76, 79, 81, 79, 77, 79, 79, 78, 79, 82, 76, 73, 64)
air <- c(3, 5, 7, 18, 43, 85, 91, 98, 100, 130, 230, 487)
emit("el_grav", EL.fixed(grav, n.t = 8))
emit("el_air", EL.fixed(air, n.t = 6))
emit("eef_grav", EEF.fixed(grav, n.t = 6))
emit("eef_air", EEF.fixed(air, n.t = 5))
set.seed(11)
y <- rnorm(18) + 4
emit("el_norm", EL.fixed(y, n.t = 7))
emit("eef_norm", EEF.fixed(y, n.t = 4))
cat("Y\n", paste(sprintf("%.17g", y), collapse = " "), "\n", sep = "")
"""

_R_LIK = r"""
suppressPackageStartupMessages(library(boot))
like <- cbind(seq(0, 1, length.out = 11),
              c(-8, -5, -3, -1.5, -0.4, 0, -0.3, -1.2, -2.5, -4, -7))
run <- function(name, expr) {
  out <- tryCatch(expr, error = function(e) paste0("ERR ", conditionMessage(e)))
  cat(name, "\n", sep = "")
  if (is.character(out)) cat(out, "\n", sep = "")
  else cat(paste(sprintf("%.17g", out), collapse = " "), "\n", sep = "")
}
run("span", lik.CI(like, -10))
run("interior", lik.CI(like, -1))
run("one", lik.CI(like, -0.05))
run("none", lik.CI(like, 0.1))
run("na", lik.CI(cbind(1:4, c(NA, -1, 0, -1)), -0.5))
run("left", lik.CI(cbind(1:6, c(0, -0.2, -1, -2, -3, -4)), -0.5))
run("right", lik.CI(cbind(1:6, c(-4, -3, -2, -1, -0.2, 0)), -0.5))
run("empty", lik.CI(cbind(numeric(0), numeric(0)), -1))
run("vector", lik.CI(1:5, -1))
run("limna", lik.CI(like, NA))
"""

_R_CORR = r"""
data <- rbind(
  c(2.12, 2.47), c(4.35, 4.61), c(3.39, 5.26), c(2.51, 3.02),
  c(4.04, 6.36), c(5.10, 5.93), c(3.77, 3.93), c(3.35, 4.09),
  c(4.10, 4.88), c(3.35, 3.81), c(4.15, 4.74), c(3.56, 3.29),
  c(3.39, 5.55), c(1.88, 2.82), c(2.56, 4.23), c(2.96, 3.23),
  c(2.49, 2.56), c(3.03, 4.31), c(2.66, 4.37), c(3.00, 2.40)
)
corr.fun <- function(d, w = rep(1, nrow(d)) / nrow(d)) {
  x <- d[, 1L]; y <- d[, 2L]
  w <- w / sum(w)
  n <- nrow(d)
  m1 <- sum(x * w)
  m2 <- sum(y * w)
  v1 <- sum(x^2 * w) - m1^2
  v2 <- sum(y^2 * w) - m2^2
  rho <- (sum(x * y * w) - m1 * m2) / sqrt(v1 * v2)
  i <- rep(1L:n, round(n * w))
  us <- (x[i] - m1) / sqrt(v1)
  xs <- (y[i] - m2) / sqrt(v2)
  L <- us * xs - 0.5 * rho * (us^2 + xs^2)
  c(rho, sum(L^2) / nrow(d)^2)
}
w <- c(0.02, 0.03, 0.05, 0.1, 0.02, 0.08, 0.04, 0.06, 0.07, 0.03,
       0.05, 0.04, 0.06, 0.05, 0.04, 0.03, 0.07, 0.06, 0.05, 0.05)
cat(paste(sprintf("%.17g", corr.fun(data, w)), collapse = " "), "\n", sep = "")
cat(paste(sprintf("%.17g", corr.fun(data)), collapse = " "), "\n", sep = "")
"""


def _r(script: str) -> str:
    if shutil.which("Rscript") is None:
        pytest.fail("Rscript is not installed")
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    return result.stdout


def _parse_vector(line: str) -> np.ndarray:
    values = []
    for token in line.split():
        values.append(np.nan if token == "NA" else float(token))
    return np.asarray(values, dtype=np.float64)


def _blocks(stdout: str) -> dict[str, str]:
    lines = [line for line in stdout.splitlines() if line != ""]
    return {lines[i]: lines[i + 1] for i in range(0, len(lines), 2)}


def _same(got: np.ndarray, ref: np.ndarray) -> None:
    got = np.asarray(got, dtype=np.float64)
    ref = np.asarray(ref, dtype=np.float64)
    assert got.shape == ref.shape
    assert np.array_equal(np.isnan(got), np.isnan(ref))
    assert np.array_equal(np.isposinf(got), np.isposinf(ref))
    assert np.array_equal(np.isneginf(got), np.isneginf(ref))
    both_missing = np.isnan(got) | np.isinf(got)
    if np.any(~both_missing):
        assert np.max(np.abs(got[~both_missing] - ref[~both_missing])) < TOLERANCE


@pytest.fixture(scope="module")
def profiles():
    text = _r(_R_PROFILES)
    blocks = _blocks(text)
    y = _parse_vector(blocks.pop("Y"))
    return blocks, y


@pytest.fixture(scope="module")
def lik_reference():
    return _blocks(_r(_R_LIK))


def test_version_is_installed():
    text = _r('cat(packageDescription("boot")$Version, "\\n")')
    assert text.strip() == "1.3-32"


def test_el_profile_matches_corrected_nlm(profiles):
    blocks, y = profiles
    _same(el_profile(GRAV7, n_t=8), _parse_vector(blocks["el_grav"]).reshape(8, 3))
    _same(el_profile(AIR, n_t=6), _parse_vector(blocks["el_air"]).reshape(6, 3))
    _same(el_profile(y, n_t=7), _parse_vector(blocks["el_norm"]).reshape(7, 3))


def test_eef_profile_matches_glm(profiles):
    blocks, y = profiles
    _same(eef_profile(GRAV7, n_t=6), _parse_vector(blocks["eef_grav"]).reshape(7, 4))
    _same(eef_profile(AIR, n_t=5), _parse_vector(blocks["eef_air"]).reshape(6, 4))
    _same(eef_profile(y, n_t=4), _parse_vector(blocks["eef_norm"]).reshape(5, 4))


def test_lik_ci_matches_installed(lik_reference):
    like = np.column_stack(
        [
            np.linspace(0, 1, 11),
            [-8, -5, -3, -1.5, -0.4, 0, -0.3, -1.2, -2.5, -4, -7],
        ]
    )
    _same(lik_ci(like, -10), _parse_vector(lik_reference["span"]))
    _same(lik_ci(like, -1), _parse_vector(lik_reference["interior"]))
    _same(
        lik_ci(np.column_stack([np.arange(1, 7), [0, -0.2, -1, -2, -3, -4]]), -0.5),
        _parse_vector(lik_reference["left"]),
    )
    _same(
        lik_ci(np.column_stack([np.arange(1, 7), [-4, -3, -2, -1, -0.2, 0]]), -0.5),
        _parse_vector(lik_reference["right"]),
    )
    with pytest.raises(ValueError, match="only one point"):
        lik_ci(like, -0.05)
    assert "only one point" in lik_reference["one"]
    with pytest.raises(ValueError, match="0 \\(non-NA\\) cases"):
        lik_ci(like, 0.1)
    assert lik_reference["none"].startswith("ERR")
    with pytest.raises(ValueError, match="never exceeds"):
        lik_ci(np.column_stack([np.arange(1, 5), [np.nan, -1, 0, -1]]), -0.5)
    with pytest.raises(ValueError, match="0 \\(non-NA\\) cases"):
        lik_ci(np.zeros((0, 2)), -1)
    with pytest.raises(ValueError, match="incorrect number of dimensions"):
        lik_ci(np.arange(5), -1)
    with pytest.raises(ValueError, match="never exceeds NA"):
        lik_ci(like, float("nan"))


def test_nested_correlation_statistic():
    lines = _r(_R_CORR).splitlines()
    data = np.array(
        [
            [2.12, 2.47], [4.35, 4.61], [3.39, 5.26], [2.51, 3.02],
            [4.04, 6.36], [5.10, 5.93], [3.77, 3.93], [3.35, 4.09],
            [4.10, 4.88], [3.35, 3.81], [4.15, 4.74], [3.56, 3.29],
            [3.39, 5.55], [1.88, 2.82], [2.56, 4.23], [2.96, 3.23],
            [2.49, 2.56], [3.03, 4.31], [2.66, 4.37], [3.00, 2.40],
        ],
        dtype=np.float64,
    )
    weights = np.array(
        [0.02, 0.03, 0.05, 0.1, 0.02, 0.08, 0.04, 0.06, 0.07, 0.03,
         0.05, 0.04, 0.06, 0.05, 0.04, 0.03, 0.07, 0.06, 0.05, 0.05]
    )
    _same(_corr_fun(data, weights), _parse_vector(lines[0]))
    _same(_corr_fun(data), _parse_vector(lines[1]))
    from boot.rng import set_seed

    reference = _r(
        """
        suppressPackageStartupMessages(library(boot))
        set.seed(1)
        w <- rep(1/20, 20)
        out <- nested.corr(cd4, w, corr(cd4), M=15)
        cat(sprintf("%.17g %.17g\\n", out[1], out[2]))
        """
    )
    set_seed(1)
    got = nested_corr(data, np.full(20, 1.0 / 20.0), 0.7231653678920299, 15)
    _same(got, _parse_vector(reference))
