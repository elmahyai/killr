"""Saddlepoint checks against installed boot 1.3-32.

The dontrun multinomial saddle.distn is omitted: R stops with
"unable to find range". lines.saddle.distn drops the Rd example's
boot(R = 9999) and draws the air-conditioning conditional density.
"""

from __future__ import annotations

import shutil
import subprocess

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pytest

from boot.data_sets import aircondit, bigcity, city
from boot.saddle import lines_saddle_distn, print_saddle_distn, saddle, saddle_distn

TOLERANCE = 1e-8
# The city alpha = 0.001 quantile sits on a rank-deficient smoothing spline.
CITY_QUANTILE_TOLERANCE = 6e-8
# sqrt(var.linear(empinf(...))) for the city ratio. empinf is not in this module.
CITY_V = 0.032487013940940376

_R = r"""
suppressPackageStartupMessages(library(boot))
stopifnot(packageDescription("boot")$Version == "1.3-32")
emit <- function(name, value) cat(name, paste(sprintf("%a", as.numeric(value)), collapse = " "), "\n")

hours <- aircondit$hours
sp1 <- saddle(A = hours/12, u = 80)
emit("SP1_SPA", sp1$spa)
emit("SP1_ZETA", sp1$zeta.hat)
sp2 <- saddle(A = cbind(hours/12, 1), u = c(80, 12), wdist = "p", type = "cond")
emit("SP2_SPA", sp2$spa)
emit("SP2_ZETA", sp2$zeta.hat)
emit("SP2_ZETA2", sp2$zeta2.hat)
sp3 <- saddle(A = cbind(hours/12, 1), u = c(80, 12), wdist = "p", type = "cond", LR = TRUE)
emit("SP3_SPA", sp3$spa)
city.sp1 <- saddle(A = city$x - 1.25 * city$u, u = 0)
emit("CITY_SPA", city.sp1$spa)
emit("CITY_ZETA", city.sp1$zeta.hat)

air.t0 <- c(mean(hours), sqrt(var(hours)/12))
air <- saddle.distn(A = cbind(hours/12, 1), u = 12, wdist = "p", type = "cond", t0 = air.t0)
emit("AIR_Q", air$quantiles[, 2])
emit("AIR_PTS", air$points)

ratio <- function(d, w) sum(d$x * w)/sum(d$u * w)
city.v <- var.linear(empinf(data = city, statistic = ratio))
bigcity.t0 <- c(mean(bigcity$x)/mean(bigcity$u), sqrt(city.v))
Afn <- function(t, data) cbind(data$x - t * data$u, 1)
ufn <- function(t, data) c(0, 10)
big <- saddle.distn(A = Afn, u = ufn, wdist = "b", type = "cond", t0 = bigcity.t0, data = bigcity)
emit("BIG_Q", big$quantiles[, 2])
emit("BIG_PTS", big$points)

Afn2 <- function(t, data) cbind(data$x - t * data$u, data$u, 1)
ufn2 <- function(t, data) c(0, sum(data$u), 10)
city.t0 <- c(mean(city$x)/mean(city$u), sqrt(city.v))
ct <- saddle.distn(A = Afn2, u = ufn2, wdist = "p", type = "cond", t0 = city.t0, data = city)
emit("CITY_Q", ct$quantiles[, 2])
emit("CITY_PTS", ct$points)

tt <- air$points[, 1]
rg <- range(tt)
tt1 <- seq.int(rg[1], rg[2], length.out = 50)
spl <- smooth.spline(tt, log(air$points[, 2]))
emit("LINES_X", tt1)
emit("LINES_Y", exp(predict(spl, tt1)$y))
cat("PRINT_START\n")
writeLines(capture.output(print(air)))
cat("PRINT_END\n")
"""


def _max_diff(got, expected):
    got = np.asarray(got, dtype=float)
    expected = np.asarray(expected, dtype=float)
    if expected.shape != got.shape and expected.size == got.size:
        expected = expected.reshape(got.shape, order="F")
    return float(np.max(np.abs(got - expected)))


@pytest.fixture(scope="module")
def reference():
    if shutil.which("Rscript") is None:
        pytest.fail("Rscript is not installed")
    result = subprocess.run(["Rscript", "-e", _R], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(result.stderr)
    rows = {}
    for line in result.stdout.splitlines():
        if line.startswith("PRINT_"):
            break
        name, rest = line.split(maxsplit=1)
        rows[name] = np.array([float.fromhex(piece) for piece in rest.split()])
    printed = result.stdout.split("PRINT_START\n", 1)[1].split("PRINT_END\n", 1)[0]
    return rows, printed


def _air_distn():
    hours = aircondit()[1][:, 0]
    air_t0 = np.array([hours.mean(), np.sqrt(np.var(hours, ddof=1) / 12.0)])
    distn = saddle_distn(
        A=np.column_stack([hours / 12.0, np.ones(len(hours))]),
        u=12,
        wdist="p",
        type="cond",
        t0=air_t0,
    )
    return distn


def _ratio_distns():
    cu = city()[1]
    bu = bigcity()[1]
    big_t0 = np.array([bu[:, 1].mean() / bu[:, 0].mean(), np.sqrt(CITY_V)])
    city_t0 = np.array([cu[:, 1].mean() / cu[:, 0].mean(), np.sqrt(CITY_V)])
    big = saddle_distn(
        A=lambda t, data: np.column_stack([data[:, 1] - t * data[:, 0], np.ones(len(data))]),
        u=lambda t, data: np.array([0.0, 10.0]),
        wdist="b",
        type="cond",
        t0=big_t0,
        data=bu,
    )
    ct = saddle_distn(
        A=lambda t, data: np.column_stack(
            [data[:, 1] - t * data[:, 0], data[:, 0], np.ones(len(data))]
        ),
        u=lambda t, data: np.array([0.0, float(np.sum(data[:, 0])), 10.0]),
        wdist="p",
        type="cond",
        t0=city_t0,
        data=cu,
    )
    return big, ct


def test_saddle_matches_r(reference):
    rows, _printed = reference
    hours = aircondit()[1][:, 0]
    cu = city()[1]
    sp1 = saddle(A=hours / 12.0, u=80)
    sp2 = saddle(
        A=np.column_stack([hours / 12.0, np.ones(12)]),
        u=np.array([80.0, 12.0]),
        wdist="p",
        type="cond",
    )
    sp3 = saddle(
        A=np.column_stack([hours / 12.0, np.ones(12)]),
        u=np.array([80.0, 12.0]),
        wdist="p",
        type="cond",
        LR=True,
    )
    city_sp = saddle(A=cu[:, 1] - 1.25 * cu[:, 0], u=0)
    diffs = [
        _max_diff(sp1["spa"], rows["SP1_SPA"]),
        _max_diff(sp1["zeta.hat"], rows["SP1_ZETA"]),
        _max_diff(sp2["spa"], rows["SP2_SPA"]),
        _max_diff(sp2["zeta.hat"], rows["SP2_ZETA"]),
        _max_diff(sp2["zeta2.hat"], rows["SP2_ZETA2"]),
        _max_diff(sp3["spa"], rows["SP3_SPA"]),
        _max_diff(city_sp["spa"], rows["CITY_SPA"]),
        _max_diff(city_sp["zeta.hat"], rows["CITY_ZETA"]),
    ]
    assert max(diffs) <= TOLERANCE


def test_saddle_distn_and_print_match_r(reference):
    rows, printed = reference
    air = _air_distn()
    big, ct = _ratio_distns()
    assert _max_diff(air["quantiles"][:, 1], rows["AIR_Q"]) <= TOLERANCE
    assert _max_diff(big["quantiles"][:, 1], rows["BIG_Q"]) <= TOLERANCE
    assert _max_diff(ct["quantiles"][:, 1], rows["CITY_Q"]) <= CITY_QUANTILE_TOLERANCE
    assert _max_diff(air["points"], rows["AIR_PTS"]) <= TOLERANCE
    assert _max_diff(big["points"], rows["BIG_PTS"]) <= TOLERANCE
    assert _max_diff(ct["points"], rows["CITY_PTS"]) <= TOLERANCE
    text = print_saddle_distn(air)
    assert "Saddlepoint Distribution Approximations" in text
    assert "Quantiles of the Distribution" in text
    assert "Lugananni-Rice" not in text

    def quantile_fields(body):
        fields = []
        for line in body.splitlines():
            if "%" not in line:
                continue
            fields.append(line.split("%", 1)[1].strip())
        return fields

    assert quantile_fields(text) == quantile_fields(printed)


def test_lines_saddle_distn_matches_r(reference):
    rows, _printed = reference
    drawn = lines_saddle_distn(_air_distn())
    assert _max_diff(drawn["x"], rows["LINES_X"]) <= TOLERANCE
    assert _max_diff(drawn["y"], rows["LINES_Y"]) <= TOLERANCE
