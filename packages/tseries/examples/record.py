"""Compare tseries 0.10-63 with R and write the translation records."""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "output"
PROOF = ROOT / "proof"

NOISE = [
    -0.59103110258436842, 0.026594369016167005, -1.516553097081865, -1.3626533492958086,
    1.1784891560316197, -0.93415131967336518, 1.3236056462120183, 0.62491778994471359,
    -0.045722955706094727, -1.0041205756722797, -0.82843323666395785, -0.34835172517298096,
    -1.5382933970870489, -0.25556524546495329, -1.1499450327075535, 0.012326967679467856,
    -0.2229695407476216, 0.88777164791130292, -0.59215527987674577, -0.65571811858088602,
    -0.6825176222150191, -0.015858192728274358, -0.44260478535504522, 0.35255749944881609,
    0.073170582291403163, 0.0071588003806459044, -0.18760011060225229, -0.76570064552538997,
    -0.22105682074495839, -0.98358858747019573, -1.1042840421509679, -0.93815021417836408,
    0.67862424418257405, -1.5774978652948257, -0.86993845822564142, 0.48467704535710099,
    -0.18605269864439059, 1.5455547001836638, -0.61138007012819973, -0.3477564873363454,
    -1.6365163055394207, 0.020381440100037087, 0.89174268016784064, -0.87274968325225077,
    0.89005082983947781, -0.34387434612934781, -2.1867813683280022, 0.8800581814920434,
    0.72385655614642541, 0.21985268026050242,
]

ORDER = """
adf.test approx.irts arma as.irts bds.test daysecond garch garch.control
get.hist.quote irts is.businessday is.irts is.weekend jarque.bera.test
kpss.test maxdrawdown na.remove plotOHLC po.test portfolio.optim pp.test
quadmap read.irts read.matrix read.ts runs.test seqplot.ts sharpe sterling
surrogate terasvirta.test tsbootstrap value weekday white.test write.irts
USeconomic NelPlo bev camp ice.river nino tcm tcmd
""".split()

UNFINISHED = {
    "arma": "arma() minimises the conditional sum of squares with stats::optim (Nelder-Mead and a Hessian). That optimiser is not translated, so the coefficients are not checked.",
    "garch": "garch() fits the model with the PORT SUMSL routine in src/dsumsl.f. That optimiser is not translated, so the coefficients are not checked.",
    "get.hist.quote": "get.hist.quote() downloads prices with quantmod::getSymbols and wraps them with zoo::zoo and zoo::index. Those are not translated.",
}

PY_HEADER = '''
import json
import math
import statistics
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.simplefilter("ignore")
import numpy as np
from boot.rng import set_seed
from tseries import *
from tseries.datasets import ice_river

NOISE = ''' + repr(NOISE) + '''

def cell(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, float):
        if value != value:
            return "NaN"
        return format(value, ".17g")
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)

def join(values):
    return ",".join(cell(value) for value in np.ravel(values))

def series_text(obj):
    values = np.asarray(obj.values, float)
    finite = values[np.isfinite(values)]
    names = ",".join(obj.names)
    return "|".join([
        str(values.size),
        cell(obj.start),
        cell(obj.end),
        cell(obj.frequency),
        names,
        cell(float(finite[0])),
        cell(float(finite[-1])),
        str(int(values.size - finite.size)),
    ])

def stamps():
    text = ("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00")
    return [datetime.strptime(item, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() for item in text]
'''

R_HEADER = r"""
suppressPackageStartupMessages(library(tseries))
options(warn = -1)
cell <- function(v) {
  if (is.logical(v)) return(if (isTRUE(v)) "TRUE" else "FALSE")
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    return(sprintf("%.17g", v))
  }
  as.character(v)
}
join <- function(x) paste(vapply(as.vector(x), cell, ""), collapse = ",")
series_text <- function(name) {
  data(list = name, package = "tseries", envir = environment())
  x <- get(name, inherits = FALSE)
  tp <- tsp(x)
  nm <- colnames(x)
  if (is.null(nm)) nm <- ""
  finite <- x[is.finite(x)]
  paste(length(x), cell(tp[1]), cell(tp[2]), cell(tp[3]), paste(nm, collapse = ","),
        cell(finite[1]), cell(finite[length(finite)]), sum(!is.finite(x)), sep = "|")
}
"""

LOOP_PY = """
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print(statistics.median(elapsed))
"""

LOOP_R = r"""
value <- one()
if (is.null(value)) value <- "NULL"
if (!is.character(value)) value <- as.character(value)
if (length(value) != 1) value <- paste(value, collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sprintf("%.17g", median(elapsed) * 1000), "\n", sep = "")
"""


def case(name, python, desc, label, r, py, loads=None, example=False):
    return {
        "name": name,
        "python": python,
        "desc": desc,
        "label": label,
        "r": textwrap.dedent(r).strip("\n"),
        "py": textwrap.dedent(py).strip("\n"),
        "loads": loads or [],
        "example": example,
    }


CASES = [
    case("adf.test", "tseries.adf_test",
         "Augmented Dickey-Fuller statistic and the tabulated p-value. The lag is trunc((n-1)^(1/3)).",
         "rnorm(50) from set.seed(11)",
         """
         set.seed(11)
         x <- rnorm(50)
         a <- adf.test(x)
         paste(cell(a$statistic), cell(a$p.value), a$parameter, sep = "|")
         """,
         """
         a = adf_test(NOISE)
         return "|".join([cell(a["statistic"]), cell(a["p_value"]), str(a["parameter"])])
         """),
    case("approx.irts", "tseries.approx_irts",
         "Linear interpolation of an irregular series onto a POSIXct grid.",
         "three GMT stamps",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         obj <- irts(tms, c(1/3, 1.23, 10))
         grid <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-06 12:00:00"), tz = "GMT")
         join(value(approx.irts(obj, grid)))
         """,
         """
         obj = irts(stamps(), [1/3, 1.23, 10])
         return join(value(approx_irts(obj, [stamps()[0], stamps()[2]])))
         """),
    case("as.irts", "tseries.as_irts",
         "The first column is the time and the remaining columns are the value.",
         "two-column matrix",
         """
         ai <- as.irts(cbind(c(1, 2, 3), c(4, 5, 6)))
         paste(join(as.numeric(time(ai))), join(value(ai)), sep = "|")
         """,
         """
         ai = as_irts([[1, 4], [2, 5], [3, 6]])
         return join(ai.time) + "|" + join(value(ai))
         """),
    case("bds.test", "tseries.bds_test",
         "Brock-Dechert-Scheinkman statistic. Close pairs are counted directly; the C bit grid is only a faster count of the same pairs.",
         "sine series, m=3, two epsilons",
         """
         x <- sin((1:40)/3) + 0.1 * (1:40)
         b <- bds.test(x, m = 3, eps = c(0.5, 1))
         join(b$statistic)
         """,
         """
         x = np.array([math.sin(i / 3) + 0.1 * i for i in range(1, 41)])
         b = bds_test(x, m=3, eps=[0.5, 1])
         return join(np.ravel(b["statistic"], order="F"))
         """),
    case("daysecond", "tseries.daysecond",
         "Seconds after midnight in the given zone. The default zone is GMT.",
         "three GMT stamps",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         join(daysecond(irts(tms, c(1, 2, 3))))
         """,
         """
         return join(daysecond(irts(stamps(), [1, 2, 3])))
         """),
    case("garch.control", "tseries.garch_control",
         "Default SUMSL tolerances. abstol, reltol, and xtol are powers of double epsilon.",
         "defaults",
         """
         g <- garch.control()
         paste(g$maxiter, cell(g$trace), g$grad, cell(g$abstol), cell(g$reltol), cell(g$xtol), cell(g$falsetol), sep = "|")
         """,
         """
         g = garch_control()
         return "|".join([str(g["maxiter"]), cell(g["trace"]), g["grad"], cell(g["abstol"]), cell(g["reltol"]), cell(g["xtol"]), cell(g["falsetol"])])
         """),
    case("irts", "tseries.irts",
         "An irregular series stores POSIX times and a value of the same length.",
         "three GMT stamps",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         obj <- irts(tms, c(1/3, 1.23, 10))
         paste(join(as.numeric(time(obj))), join(value(obj)), sep = "|")
         """,
         """
         obj = irts(stamps(), [1/3, 1.23, 10])
         return join(obj.time) + "|" + join(value(obj))
         """),
    case("is.businessday", "tseries.is_businessday",
         "Monday through Friday, using POSIXlt wday in the given zone.",
         "Friday, Saturday, Sunday",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         paste(is.businessday(irts(tms, 1:3)), collapse = ",")
         """,
         """
         return ",".join(cell(v) for v in is_businessday(irts(stamps(), [1, 2, 3])))
         """),
    case("is.irts", "tseries.is_irts",
         "TRUE for an irts object.",
         "one series",
         """
         obj <- irts(as.POSIXct("1991-01-04 17:00:00", tz = "GMT"), 1)
         paste(is.irts(obj), is.irts(1), sep = "|")
         """,
         """
         obj = irts(stamps()[:1], [1])
         return cell(is_irts(obj)) + "|" + cell(is_irts(1))
         """),
    case("is.weekend", "tseries.is_weekend",
         "Sunday or Saturday.",
         "Friday, Saturday, Sunday",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         paste(is.weekend(irts(tms, 1:3)), collapse = ",")
         """,
         """
         return ",".join(cell(v) for v in is_weekend(irts(stamps(), [1, 2, 3])))
         """),
    case("jarque.bera.test", "tseries.jarque_bera_test",
         "Skewness and kurtosis use the divisor n. The p-value is the chi-square tail on 2 degrees of freedom.",
         "the seeded normal sample",
         """
         set.seed(11)
         j <- jarque.bera.test(rnorm(50))
         paste(cell(j$statistic), cell(j$p.value), sep = "|")
         """,
         """
         j = jarque_bera_test(NOISE)
         return cell(j["statistic"]) + "|" + cell(j["p_value"])
         """),
    case("kpss.test", "tseries.kpss_test",
         "KPSS level statistic. The long-run variance is the Phillips-Perron weighted sum.",
         "the seeded normal sample",
         """
         set.seed(11)
         k <- kpss.test(rnorm(50))
         paste(cell(k$statistic), cell(k$p.value), k$parameter, sep = "|")
         """,
         """
         k = kpss_test(NOISE)
         return "|".join([cell(k["statistic"]), cell(k["p_value"]), str(k["parameter"])])
         """),
    case("maxdrawdown", "tseries.maxdrawdown",
         "The deepest drop from a running peak, and the 1-based peak and trough.",
         "1, 3, 2, 5, 1, 4",
         """
         md <- maxdrawdown(c(1, 3, 2, 5, 1, 4))
         paste(cell(md$maxdrawdown), paste(md$from, collapse = ","), paste(md$to, collapse = ","), sep = "|")
         """,
         """
         md = maxdrawdown([1, 3, 2, 5, 1, 4])
         return cell(md["maxdrawdown"]) + "|" + ",".join(str(v) for v in md["from"]) + "|" + ",".join(str(v) for v in md["to"])
         """),
    case("na.remove", "tseries.na_remove",
         "Drops missing rows and records the 1-based positions. A time series rebuilds tsp from the remaining span.",
         "a vector and a quarterly series",
         """
         nr <- na.remove(c(1, NA, 3, NA, 5))
         tz <- na.remove(ts(c(1, NA, 3, 4, NA, 6), start = c(2000, 1), frequency = 4))
         paste(join(nr), paste(attr(nr, "na.removed"), collapse = ","), join(as.numeric(tz)),
               paste(attr(tz, "na.removed"), collapse = ","), paste(vapply(tsp(tz), cell, ""), collapse = ","), sep = "|")
         """,
         """
         kept, removed = na_remove([1, float("nan"), 3, float("nan"), 5])
         tk, tr, tsp = na_remove([1, float("nan"), 3, 4, float("nan"), 6], tsp=(2000, 2001.25, 4))
         return "|".join([join(kept), ",".join(str(int(v)) for v in removed), join(tk), ",".join(str(int(v)) for v in tr), join(tsp)])
         """),
    case("plotOHLC", "tseries.plot_ohlc",
         "High-low segment, open tick, and close tick. The check is those coordinates. Calendar labels treat the time unit as days since 1899-12-30.",
         "five daily bars from 2000",
         """
         oh <- ts(cbind(Open = c(1, 2, 3, 4, 5), High = c(2, 3, 4, 5, 6), Low = c(0, 1, 2, 3, 4), Close = c(1, 2, 1, 3, 2)), start = 2000, frequency = 1)
         time.x <- time(oh)
         dt <- min(lag(time.x) - time.x) / 3
         n <- NROW(oh)
         lab.ind <- round(seq(1, n, length.out = 5))
         D <- as.vector(time.x[lab.ind] * 86400) + as.POSIXct("1899-12-30", tz = "GMT")
         labs <- format(D, "%Y-%m-%d", tz = "GMT")
         rows <- vapply(seq_len(n), function(i) paste(cell(time.x[i]), cell(oh[i, "High"]), cell(oh[i, "Low"]), cell(time.x[i] - dt), cell(oh[i, "Open"]), cell(oh[i, "Close"]), cell(time.x[i] + dt), sep = ","), "")
         paste0(paste(rows, collapse = "|"), "#", paste(labs, collapse = ","))
         """,
         """
         oh = np.column_stack([[1, 2, 3, 4, 5], [2, 3, 4, 5, 6], [0, 1, 2, 3, 4], [1, 2, 1, 3, 2]])
         return plot_ohlc(oh, start=2000, frequency=1)
         """),
    case("po.test", "tseries.po_test",
         "Phillips-Ouliaris statistic on two columns, with the longer lag.",
         "sine and cosine",
         """
         x <- sin((1:40)/3) + 0.1 * (1:40)
         y <- cos((1:40)/5)
         po <- po.test(cbind(x, y), lshort = FALSE)
         paste(cell(po$statistic), cell(po$p.value), po$parameter, sep = "|")
         """,
         """
         x = np.array([math.sin(i / 3) + 0.1 * i for i in range(1, 41)])
         y = np.array([math.cos(i / 5) for i in range(1, 41)])
         po = po_test(np.column_stack([x, y]), lshort=False)
         return "|".join([cell(po["statistic"]), cell(po["p_value"]), str(po["parameter"])])
         """),
    case("portfolio.optim", "tseries.portfolio_optim",
         "Mean-variance weights from quadprog.solve_qp. The covariance is the sample covariance.",
         "rnorm matrix from set.seed(3), shifted by 2",
         """
         set.seed(3)
         x <- matrix(rnorm(40), 10, 4) + 2
         p <- portfolio.optim(x)
         paste(join(p$pw), cell(p$pm), cell(p$ps), sep = "|")
         """,
         """
         flat = [1.0380665840801173,1.7074742771215334,2.2587882162412516,0.8478681140848674,2.1957828262863752,2.0301239446016317,2.0854177316122717,3.1166102127152655,0.78114258442201212,3.2673687220898877,1.2552184038648591,0.86878142916426393,1.2836415099670231,2.2526523696462148,2.1520457066555956,1.6923435703215801,1.0469826690918778,1.3517571885515296,3.224313624280585,2.1998116079829697,1.4215162781400283,1.0576992665224609,1.7962718203380053,0.333525159969841,1.515544890849009,1.2589273392784048,3.1606157792413354,3.0120671249342337,1.9279215259134403,0.86321770190067793,2.9006247289826703,2.8517704470922212,2.7277151741544801,2.7365021456886098,1.6478703830543082,2.7055155134855133,3.3003579887320784,2.038252014144271,1.0207162300037216,2.7937612308725335]
         x = np.array(flat).reshape((10, 4), order="F")
         p = portfolio_optim(x)
         return join(p["pw"]) + "|" + cell(p["pm"]) + "|" + cell(p["ps"])
         """,
         ["quadprog"]),
    case("pp.test", "tseries.pp_test",
         "Phillips-Perron Z(alpha) with the long lag. The p-value is interpolated on the Dickey-Fuller table.",
         "sine wave of length 60",
         """
         p <- pp.test(sin((1:60)/3), lshort = FALSE)
         paste(cell(p$statistic), cell(p$p.value), p$parameter, sep = "|")
         """,
         """
         p = pp_test([math.sin(i / 3) for i in range(1, 61)], lshort=False)
         return "|".join([cell(p["statistic"]), cell(p["p_value"]), str(p["parameter"])])
         """),
    case("quadmap", "tseries.quadmap",
         "Logistic map x[i] = a*(1-x[i-1])*x[i-1], starting at xi.",
         "xi=0.2, a=4, n=8",
         """
         join(as.numeric(quadmap(0.2, 4, 8)))
         """,
         """
         return join(quadmap(0.2, 4, 8))
         """),
    case("read.irts", "tseries.read_irts",
         "The first tokens of the format are the time. The rest is the value matrix.",
         "two rows, two value columns",
         """
         tmp <- "/tmp/tseries-read-irts.txt"
         cat("1991-01-04 17:00:00 1.5 2.5\\n1991-01-05 09:30:00 3.5 4.5\\n", file = tmp)
         ir <- read.irts(tmp)
         paste(join(as.numeric(time(ir))), join(value(ir)), sep = "|")
         """,
         """
         path = Path("/tmp/tseries-read-irts.txt")
         path.write_text("1991-01-04 17:00:00 1.5 2.5\\n1991-01-05 09:30:00 3.5 4.5\\n")
         ir = read_irts(path)
         return join(ir.time) + "|" + join(np.ravel(value(ir), order="F"))
         """),
    case("read.matrix", "tseries.read_matrix",
         "Whitespace-separated numbers, filled row by row. A header row becomes the names.",
         "a plain matrix and a header",
         """
         tmp <- "/tmp/tseries-read-matrix.txt"
         cat("1 2 3\\n4 5 6\\n", file = tmp)
         m <- read.matrix(tmp)
         cat("a b\\n1.5 2.5\\n3.5 4.5\\n", file = tmp)
         h <- read.matrix(tmp, header = TRUE)
         paste(join(m), paste(colnames(h), collapse = ","), join(h), sep = "|")
         """,
         """
         path = Path("/tmp/tseries-read-matrix.txt")
         path.write_text("1 2 3\\n4 5 6\\n")
         m = read_matrix(path)
         path.write_text("a b\\n1.5 2.5\\n3.5 4.5\\n")
         h, names = read_matrix(path, header=True)
         return join(np.ravel(m, order="F")) + "|" + ",".join(names) + "|" + join(np.ravel(h, order="F"))
         """),
    case("read.ts", "tseries.read_ts",
         "read.matrix, then a time series with the given start and frequency.",
         "two rows from 1990, quarterly",
         """
         tmp <- "/tmp/tseries-read-ts.txt"
         cat("a b\\n1.5 2.5\\n3.5 4.5\\n", file = tmp)
         ts <- read.ts(tmp, header = TRUE, start = 1990, frequency = 4)
         paste(join(as.numeric(ts)), paste(vapply(tsp(ts), cell, ""), collapse = ","), sep = "|")
         """,
         """
         path = Path("/tmp/tseries-read-ts.txt")
         path.write_text("a b\\n1.5 2.5\\n3.5 4.5\\n")
         values, start, freq = read_ts(path, header=True, start=1990, frequency=4)
         end = start + (values.shape[0] - 1) / freq
         return join(np.ravel(values, order="F")) + "|" + ",".join([cell(start), cell(end), cell(freq)])
         """),
    case("runs.test", "tseries.runs_test",
         "The two-sided runs statistic for a two-level factor.",
         "alternating a and b",
         """
         r <- runs.test(factor(rep(c("a", "b"), 20)))
         paste(cell(r$statistic), cell(r$p.value), sep = "|")
         """,
         """
         r = runs_test(["a", "b"] * 20)
         return cell(r["statistic"]) + "|" + cell(r["p_value"])
         """),
    case("seqplot.ts", "tseries.seqplot_ts",
         "Two series on one pair of axes. The check is the shared range of time and of the finite values.",
         "two short series with different starts",
         """
         sx <- ts(c(1, 2, 4, 3), start = 1, frequency = 1)
         sy <- ts(c(0, 2, 1, 5), start = 2, frequency = 1)
         xlim <- range(time(sx), time(sy))
         ylim <- range(sx, sy)
         paste(cell(xlim[1]), cell(xlim[2]), cell(ylim[1]), cell(ylim[2]), sep = ",")
         """,
         """
         return seqplot_ts([1, 2, 4, 3], [0, 2, 1, 5], start=1, frequency=1, start_y=2, frequency_y=1)
         """),
    case("sharpe", "tseries.sharpe",
         "scale * (mean(diff(x)) - r) / sd(diff(x)). sd uses the divisor n-1. scale defaults to sqrt(250).",
         "1, 3, 2, 5, 1, 4",
         """
         cell(sharpe(c(1, 3, 2, 5, 1, 4)))
         """,
         """
         return cell(sharpe([1, 3, 2, 5, 1, 4]))
         """),
    case("sterling", "tseries.sterling",
         "(last - first) / maxdrawdown.",
         "1, 3, 2, 5, 1, 4",
         """
         cell(sterling(c(1, 3, 2, 5, 1, 4)))
         """,
         """
         return cell(sterling([1, 3, 2, 5, 1, 4]))
         """),
    case("surrogate", "tseries.surrogate",
         "A permutation, a phase surrogate, and an amplitude surrogate. The phase draw is runif and the normal draw is R's two-uniform rnorm. The inverse FFT is not divided by n.",
         "eight sines, set.seed(1)",
         """
         z <- sin((1:8)/3)
         set.seed(1); a <- surrogate(z, fft = FALSE)
         set.seed(1); b <- surrogate(z, fft = TRUE)
         set.seed(1); c <- surrogate(z, fft = TRUE, amplitude = TRUE)
         set.seed(4); d <- surrogate(sin((1:10)/3), ns = 2, statistic = function(v) v[1])
         paste(join(a), join(b), join(c), cell(d$orig.statistic), cell(d$bias), join(d$statistic), sep = "|")
         """,
         """
         z = np.array([math.sin(i / 3) for i in range(1, 9)])
         set_seed(1); a = surrogate(z, fft=False)
         set_seed(1); b = surrogate(z, fft=True)
         set_seed(1); c = surrogate(z, fft=True, amplitude=True)
         set_seed(4); d = surrogate(np.array([math.sin(i / 3) for i in range(1, 11)]), ns=2, statistic=lambda v: v[0])
         return "|".join([join(a), join(b), join(c), cell(float(np.ravel(d["orig_statistic"])[0])), cell(float(np.ravel(d["bias"])[0])), join(d["statistic"])])
         """,
         ["boot", "extraDistr"]),
    case("terasvirta.test", "tseries.terasvirta_test",
         "The time-series method. The statistic uses the original length, and the name keeps the Teraesvirta spelling.",
         "sine series, lag 1",
         """
         te <- terasvirta.test(ts(sin((1:40)/3)))
         paste(cell(te$statistic), cell(te$p.value), sep = "|")
         """,
         """
         te = terasvirta_test([math.sin(i / 3) for i in range(1, 41)])
         return cell(te["statistic"]) + "|" + cell(te["p_value"])
         """),
    case("tsbootstrap", "tseries.tsbootstrap",
         "Stationary and block bootstrap. The start index is (int)(unif_rand()*n+1). The stationary length is Ahrens-Dieter exp_rand.",
         "twelve sines, set.seed(1)",
         """
         z <- sin((1:12)/3)
         set.seed(1); a <- tsbootstrap(z, b = 4, type = "stationary")
         set.seed(1); b <- tsbootstrap(z, b = 4, type = "block")
         set.seed(4); c <- tsbootstrap(sin((1:16)/3), nb = 2, statistic = function(v) v[1], b = 5, type = "block")
         paste(join(a), join(b), cell(c$orig.statistic), cell(c$bias), join(c$statistic), sep = "|")
         """,
         """
         z = np.array([math.sin(i / 3) for i in range(1, 13)])
         set_seed(1); a = tsbootstrap(z, b=4, type="stationary")
         set_seed(1); b = tsbootstrap(z, b=4, type="block")
         set_seed(4); c = tsbootstrap(np.array([math.sin(i / 3) for i in range(1, 17)]), nb=2, statistic=lambda v: v[0], b=5, type="block")
         return "|".join([join(a), join(b), cell(float(np.ravel(c["orig_statistic"])[0])), cell(float(np.ravel(c["bias"])[0])), join(c["statistic"])])
         """,
         ["boot", "extraDistr"]),
    case("value", "tseries.value",
         "The numeric value stored on an irts.",
         "1/3, 1.23, 10",
         """
         tms <- as.POSIXct("1991-01-04 17:00:00", tz = "GMT") + c(0, 86400)
         join(value(irts(tms, c(1/3, 1.23))))
         """,
         """
         return join(value(irts([stamps()[0], stamps()[0] + 86400], [1/3, 1.23])))
         """),
    case("weekday", "tseries.weekday",
         "POSIXlt wday: 0 is Sunday.",
         "Friday, Saturday, Sunday",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         paste(weekday(irts(tms, 1:3)), collapse = ",")
         """,
         """
         return ",".join(str(int(v)) for v in weekday(irts(stamps(), [1, 2, 3])))
         """),
    case("white.test", "tseries.white_test",
         "White's neural-network test for a series. The phantom directions are runif, then the principal-component scores from the second column on.",
         "length 40, set.seed(1), q=4, qstar=1",
         """
         set.seed(1)
         w <- white.test(ts(sin((1:40)/3) + 0.1 * (1:40)), q = 4, qstar = 1)
         paste(cell(w$statistic), cell(w$p.value), sep = "|")
         """,
         """
         set_seed(1)
         x = np.array([math.sin(i / 3) + 0.1 * i for i in range(1, 41)])
         w = white_test(x, q=4, qstar=1)
         return cell(w["statistic"]) + "|" + cell(w["p_value"])
         """,
         ["boot"]),
    case("write.irts", "tseries.write_irts",
         "format of the time in GMT, then formatC of the value at 4 significant digits.",
         "three stamps",
         """
         tms <- as.POSIXct(c("1991-01-04 17:00:00", "1991-01-05 09:30:00", "1991-01-06 12:00:00"), tz = "GMT")
         tmp <- "/tmp/tseries-write-irts.txt"
         write.irts(irts(tms, c(1/3, 1.23, 10)), tmp)
         paste(readLines(tmp), collapse = "|")
         """,
         """
         text = write_irts(irts(stamps(), [1/3, 1.23, 10]), "/tmp/tseries-write-irts-py.txt")
         return text.strip().replace("\\n", "|")
         """),
]


def _dataset_cases():
    names = {
        "USeconomic": "USeconomic",
        "NelPlo": "NelPlo",
        "bev": "bev",
        "camp": "camp",
        "ice.river": "ice_river",
        "nino": "nino",
        "tcm": "tcm",
        "tcmd": "tcmd",
    }
    out = []
    for r_name, py_name in names.items():
        out.append(case(
            r_name,
            f"tseries.{py_name}",
            "The series stored in the package data. The check is the length, tsp, names, the first and last finite values, and the NA count.",
            r_name,
            f'series_text("{r_name}")',
            f"return series_text({py_name}())",
            example=True,
        ))
    return out


CASES.extend(_dataset_cases())

NUMBER = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?")


def _diff(left, right):
    if NUMBER.sub("#", left) != NUMBER.sub("#", right):
        return None
    a = [float(item) for item in NUMBER.findall(left)]
    b = [float(item) for item in NUMBER.findall(right)]
    if len(a) != len(b):
        return None
    if not a:
        return 0.0
    return max(abs(x - y) for x, y in zip(a, b))


def _run_r(cases):
    parts = [R_HEADER]
    for item in cases:
        fname = "one_" + item["name"].replace(".", "_")
        parts.append(f"{fname} <- function() {{\n{item['r']}\n}}")
        parts.append(
            f"""
value <- tryCatch({fname}(), error = function(e) paste0("ERR:", conditionMessage(e)))
if (is.null(value)) value <- "NULL"
if (!is.character(value)) value <- as.character(value)
if (length(value) != 1) value <- paste(value, collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {{
  t0 <- as.numeric(Sys.time())
  tryCatch({fname}(), error = function(e) NULL)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}}
cat("{item['name']}\\n", nchar(value), "\\n", sep = "")
cat(value, sep = "")
cat("\\n", sprintf("%.17g", median(elapsed) * 1000), "\\n", sep = "")
"""
        )
    path = Path("/tmp/tseries-batch.R")
    path.write_text("\n".join(parts))
    completed = subprocess.run(["Rscript", str(path)], check=True, capture_output=True, text=True)
    if completed.stderr.strip():
        print(completed.stderr)
    return _parse_blocks(completed.stdout)


def _parse_blocks(text):
    found = {}
    while text:
        name, text = text.split("\n", 1)
        count, text = text.split("\n", 1)
        count = int(count)
        value = text[:count]
        text = text[count:]
        if not text.startswith("\n"):
            raise RuntimeError(f"bad block after {name}")
        text = text[1:]
        ms, text = text.split("\n", 1)
        found[name] = (value, float(ms))
    return found


def _run_py(item, namespace):
    source = "def one():\n" + textwrap.indent(item["py"], "    ")
    local = dict(namespace)
    exec(source, local)
    one = local["one"]
    try:
        value = one()
    except Exception as exc:
        value = f"ERR:{exc}"
    if value is None:
        value = "NULL"
    value = str(value)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        try:
            one()
        except Exception:
            pass
        elapsed.append((time.perf_counter() - started) * 1000)
    return value, statistics.median(elapsed)


def _doc(item, value):
    side = {
        "description": item["desc"],
        "usage": f"{item['name']}()",
        "arguments": [{"name": "x", "text": "The series, matrix, or path this function accepts."}],
        "details": item["desc"],
        "value": "The same value tseries 0.10-63 returns for this case, written as one line.",
        "example": item["r"],
    }
    origin = dict(side)
    origin["output"] = f"output/{item['name']}-r.txt"
    translated = dict(side)
    translated["example"] = item["py"]
    translated["output"] = f"output/{item['name']}-python.txt"
    return {"name": item["name"], "title": item["desc"], "origin": origin, "translation": translated}


def _record(item, r_value, r_ms, py_ms, diff):
    matched = diff is not None and diff <= 1e-8 and not str(r_value).startswith("ERR:")
    speedup = None if item["example"] or not py_ms else r_ms / py_ms
    proof_r = R_HEADER + "\none <- function() {\n" + item["r"] + "\n}\n" + LOOP_R
    proof_py = PY_HEADER + "\ndef one():\n" + textwrap.indent(item["py"], "    ") + "\n" + LOOP_PY
    return {
        "name": item["name"],
        "translated": matched,
        "python": item["python"] if matched else "",
        "loads": item["loads"] if matched else [],
        "uses": [],
        "done": item["desc"] if matched else "",
        "not_done": "" if matched else "The check against tseries 0.10-63 did not match.",
        "blocked_by": [],
        "assigned": "",
        "check": {
            "case": item["label"],
            "r_ms": None if item["example"] else r_ms,
            "translated_ms": None if item["example"] else py_ms,
            "speedup": speedup,
            "matches": matched,
            "max_abs_diff": diff if matched else None,
            "tolerance": 1e-8,
            "proof": {"r": proof_r, "python": proof_py},
        },
    }


def _unfinished(name):
    return {
        "name": name,
        "translated": False,
        "python": "",
        "loads": [],
        "uses": [],
        "done": "",
        "not_done": UNFINISHED[name],
        "blocked_by": [],
        "assigned": "",
    }


def main():
    import sys

    os.environ.setdefault("MPLBACKEND", "Agg")
    for extra in ("tseries", "boot", "extraDistr", "quadprog"):
        path = str(REPO / "packages" / extra)
        if path not in sys.path:
            sys.path.insert(0, path)
    by_name = {item["name"]: item for item in CASES}
    missing = [name for name in ORDER if name not in by_name and name not in UNFINISHED]
    if missing:
        raise SystemExit("missing cases: " + ", ".join(missing))
    namespace = {}
    exec(PY_HEADER, namespace)
    r_found = _run_r(CASES)
    functions = []
    failed = []
    for name in ORDER:
        if name in UNFINISHED:
            functions.append(_unfinished(name))
            continue
        item = by_name[name]
        r_value, r_ms = r_found[name]
        py_value, py_ms = _run_py(item, namespace)
        diff = None if r_value.startswith("ERR:") or py_value.startswith("ERR:") else _diff(r_value, py_value)
        matched = diff is not None and diff <= 1e-8
        print(f"{name}: match={matched} diff={diff} r_ms={r_ms:.4f} py_ms={py_ms:.4f}")
        if not matched:
            failed.append(name)
            print(" R", r_value[:300])
            print(" P", py_value[:300])
        record = _record(item, r_value, r_ms, py_ms, diff if matched else None)
        functions.append(record)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        PROOF.mkdir(parents=True, exist_ok=True)
        (OUTPUT / f"{name}-r.txt").write_text(r_value + "\n")
        (OUTPUT / f"{name}-python.txt").write_text(py_value + "\n")
        (DOCS / f"{name}.json").write_text(json.dumps(_doc(item, r_value), indent=2) + "\n")
        proof = record["check"]["proof"]
        (PROOF / f"{name}-r.R").write_text(proof["r"])
        (PROOF / f"{name}-py.py").write_text(proof["python"])
    translated = sum(1 for item in functions if item["translated"])
    payload = {
        "name": "tseries",
        "cran_version": "0.10-63",
        "inventory": "complete",
        "status": "in_progress" if translated != len(functions) else "complete",
        "blocked_by": [],
        "crate_claims": [],
        "resume": (
            "tseries 0.10-63. The unit-root, nonlinearity, bootstrap, surrogate, portfolio, irregular-series, "
            "and finance helpers match R. portfolio.optim calls quadprog.solve_qp. "
            "get.hist.quote waits on quantmod::getSymbols and zoo. arma waits on stats::optim, "
            "and garch waits on the PORT SUMSL routine."
        ),
        "dependencies": {
            "translated": ["boot", "extraDistr", "quadprog"],
            "native": ["matplotlib", "numpy", "scipy", "zoneinfo"],
            "rust": [],
        },
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"matched {translated} of {len(functions)}")
    if failed:
        raise SystemExit("failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
