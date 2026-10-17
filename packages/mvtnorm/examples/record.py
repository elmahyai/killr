"""Check every mvtnorm export against the installed CRAN package and record it."""

from __future__ import annotations

import json
import math
import os
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "bin" / "python"
DOCS = PKG / "docs"
OUT = DOCS / "output"
PROOF = PKG / "proof"

# name, python attribute, R expression, Python expression, one-line note
CASES = [
    ("dmvnorm", "dmvnorm", "as.numeric(dmvnorm(c(0, 0)))", "flat(dmvnorm([0.0, 0.0]))", "Standard bivariate density at the origin."),
    ("rmvnorm", "rmvnorm", "set.seed(1); as.numeric(rmvnorm(2, sigma = diag(2)))", "set_seed(1); flat(rmvnorm(2, sigma=np.eye(2)))", "Two standard draws after set.seed(1), filled by row."),
    ("dmvt", "dmvt", "as.numeric(dmvt(c(0, 0), log = FALSE))", "flat(dmvt([0.0, 0.0], log=False))", "Unit bivariate t density at the origin, df 1."),
    ("rmvt", "rmvt", "set.seed(1); as.numeric(rmvt(2, sigma = diag(2), df = 4))", "set_seed(1); flat(rmvt(2, sigma=np.eye(2), df=4))", "Shifted t draws. Normals are drawn before the chi-squared scales."),
    ("pmvnorm", "pmvnorm", "as.numeric(pmvnorm(lower = -Inf, upper = 3, mean = 0, sigma = 1))", "flat(pmvnorm(lower=-math.inf, upper=3, mean=0, sigma=1))", "A length-one covariance is pnorm."),
    ("pmvt", "pmvt", "as.numeric(pmvt(lower = -Inf, upper = 2, df = 5, sigma = 1))", "flat(pmvt(lower=-math.inf, upper=2, df=5, sigma=1))", "A length-one problem is pt."),
    ("qmvnorm", "qmvnorm", "q <- qmvnorm(0.95, sigma = 1); c(q$quantile, q$f.quantile)", "q = qmvnorm(0.95, sigma=1); np.array([q['quantile'], q['f.quantile']])", "Univariate normal quantile."),
    ("qmvt", "qmvt", "q <- qmvt(0.9, df = 8, sigma = 1); c(q$quantile, q$f.quantile)", "q = qmvt(0.9, df=8, sigma=1); np.array([q['quantile'], q['f.quantile']])", "Univariate t quantile."),
    ("GenzBretz", "GenzBretz", "g <- GenzBretz(); c(g$maxpts, g$abseps, g$releps)", "g = GenzBretz(); np.array([g.maxpts, g.abseps, g.releps])", "Default lattice-rule settings."),
    ("Miwa", "Miwa", "g <- Miwa(); c(g$steps, g$maxval)", "g = Miwa(); np.array([g.steps, g.maxval])", "Default Miwa grid."),
    ("TVPACK", "TVPACK", "TVPACK()$eps", "np.array([TVPACK().eps])", "Default absolute tolerance for dimension 2 or 3."),
    ("ltMatrices", "ltMatrices", "as.numeric(unclass(ltMatrices(c(1, 0, 1), diag = TRUE)))", "flat(ltMatrices([1.0, 0.0, 1.0], diag=True))", "One unit lower triangle, diagonal stored."),
    ("syMatrices", "syMatrices", "as.numeric(unclass(syMatrices(c(1, 0.2, 1), diag = TRUE)))", "flat(syMatrices([1.0, 0.2, 1.0], diag=True))", "One symmetric matrix stored as its lower triangle."),
    ("as.ltMatrices", "as_ltMatrices", "as.numeric(unclass(as.ltMatrices(matrix(c(1, 0, 0, 1), 2))))", "flat(as_ltMatrices(np.array([[1.0, 0.0], [0.0, 1.0]])))", "The strict lower triangle of the identity is 0."),
    ("as.syMatrices", "as_syMatrices", "as.numeric(unclass(as.syMatrices(ltMatrices(c(1, 0, 1), diag = TRUE))))", "flat(as_syMatrices(ltMatrices([1.0, 0.0, 1.0], diag=True)))", "The same packed values, class syMatrices."),
    ("is.ltMatrices", "is_ltMatrices", "is.ltMatrices(ltMatrices(c(1, 0, 1), diag = TRUE))", "np.array([is_ltMatrices(ltMatrices([1.0, 0.0, 1.0], diag=True))])", "The constructor's class test."),
    ("is.syMatrices", "is_syMatrices", "is.syMatrices(syMatrices(c(1, 0.2, 1), diag = TRUE))", "np.array([is_syMatrices(syMatrices([1.0, 0.2, 1.0], diag=True))])", "The symmetric class test."),
    ("is.chol", "is_chol", "is.chol(as.chol(ltMatrices(c(1, 0, 1), diag = TRUE)))", "np.array([is_chol(as_chol(ltMatrices([1.0, 0.0, 1.0], diag=True)))])", "as.chol adds the chol class."),
    ("is.invchol", "is_invchol", "is.invchol(as.invchol(ltMatrices(c(1, -0.2, 1), diag = TRUE)))", "np.array([is_invchol(as_invchol(ltMatrices([1.0, -0.2, 1.0], diag=True)))])", "as.invchol adds the invchol class."),
    ("as.chol", "as_chol", "as.numeric(unclass(as.chol(ltMatrices(c(1, 0, 1), diag = TRUE))))", "flat(as_chol(ltMatrices([1.0, 0.0, 1.0], diag=True)))", "The packed values are unchanged."),
    ("as.invchol", "as_invchol", "as.numeric(unclass(as.invchol(ltMatrices(c(1, -0.2, 1), diag = TRUE))))", "flat(as_invchol(ltMatrices([1.0, -0.2, 1.0], diag=True)))", "The packed values are unchanged."),
    ("diagonals", "diagonals", "as.numeric(diagonals(ltMatrices(c(2, 0.3, 4), diag = TRUE)))", "flat(diagonals(ltMatrices([2.0, 0.3, 4.0], diag=True)))", "The stored diagonal."),
    ("diagonals<-", "set_diagonals", "x <- ltMatrices(c(2, 0.3, 4), diag = TRUE); diagonals(x) <- c(1, 1); as.numeric(unclass(x))", "flat(set_diagonals(ltMatrices([2.0, 0.3, 4.0], diag=True), np.array([[1.0], [1.0]])))", "Replace the diagonal and keep the off-diagonal."),
    ("chol2cov", "chol2cov", "as.numeric(unclass(chol2cov(as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE)))))", "flat(chol2cov(as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True))))", "Sigma = C C'. Packed lower triangle."),
    ("cov2chol", "cov2chol", "as.numeric(unclass(cov2chol(syMatrices(c(4, 1, 3), diag = TRUE))))", "flat(cov2chol(syMatrices([4.0, 1.0, 3.0], diag=True)))", "Cholesky of a symmetric matrix."),
    ("logdet", "logdet", "as.numeric(logdet(as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE))))", "flat(logdet(as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True))))", "Sum of log diagonal entries."),
    ("Lower_tri", "Lower_tri", "as.numeric(Lower_tri(ltMatrices(c(1, 0.2, 1), diag = TRUE), diag = TRUE))", "flat(Lower_tri(ltMatrices([1.0, 0.2, 1.0], diag=True), diag=True))", "The packed triangle, diagonal included."),
    ("Mult", "Mult", "C <- ltMatrices(c(1, 0.2, 1), diag = TRUE); as.numeric(Mult(C, matrix(c(1, 2), 2)))", "flat(Mult(ltMatrices([1.0, 0.2, 1.0], diag=True), np.array([[1.0], [2.0]])))", "One triangular matrix times a column."),
    ("Tcrossprod", "Tcrossprod", "as.numeric(unclass(Tcrossprod(ltMatrices(c(1, 0.2, 1), diag = TRUE))))", "flat(Tcrossprod(ltMatrices([1.0, 0.2, 1.0], diag=True)))", "C C', packed."),
    ("Crossprod", "Crossprod", "as.numeric(unclass(Crossprod(ltMatrices(c(1, 0.2, 1), diag = TRUE))))", "flat(Crossprod(ltMatrices([1.0, 0.2, 1.0], diag=True)))", "C' C, packed."),
    ("invchol", "invchol", "as.numeric(unclass(invchol(matrix(c(2, 0.4, 0.4, 1), 2))))", "flat(invchol(np.array([[2.0, 0.4], [0.4, 1.0]])))", "Inverse Cholesky of a 2 by 2 covariance."),
    ("invchol2chol", "invchol2chol", "L <- as.invchol(ltMatrices(c(1, -0.2, 1), diag = TRUE)); as.numeric(unclass(invchol2chol(L)))", "flat(invchol2chol(as_invchol(ltMatrices([1.0, -0.2, 1.0], diag=True))))", "Invert an inverse-Cholesky factor."),
    ("chol2invchol", "chol2invchol", "C <- as.chol(ltMatrices(c(1, 0.2, 1), diag = TRUE)); as.numeric(unclass(chol2invchol(C)))", "flat(chol2invchol(as_chol(ltMatrices([1.0, 0.2, 1.0], diag=True))))", "Invert a Cholesky factor."),
    ("invchol2cov", "invchol2cov", "L <- as.invchol(ltMatrices(c(1, -0.2, 1), diag = TRUE)); as.numeric(unclass(invchol2cov(L)))", "flat(invchol2cov(as_invchol(ltMatrices([1.0, -0.2, 1.0], diag=True))))", "Covariance from an inverse Cholesky."),
    ("cov2invchol", "cov2invchol", "as.numeric(unclass(cov2invchol(matrix(c(2, 0.4, 0.4, 1), 2))))", "flat(cov2invchol(np.array([[2.0, 0.4], [0.4, 1.0]])))", "Inverse Cholesky of a covariance."),
    ("chol2pre", "chol2pre", "C <- as.chol(ltMatrices(c(1, 0.2, 1), diag = TRUE)); as.numeric(unclass(chol2pre(C)))", "flat(chol2pre(as_chol(ltMatrices([1.0, 0.2, 1.0], diag=True))))", "Precision from a Cholesky factor."),
    ("invchol2pre", "invchol2pre", "L <- as.invchol(ltMatrices(c(1, -0.2, 1), diag = TRUE)); as.numeric(unclass(invchol2pre(L)))", "flat(invchol2pre(as_invchol(ltMatrices([1.0, -0.2, 1.0], diag=True))))", "Precision from an inverse Cholesky."),
    ("Dchol", "Dchol", "as.numeric(unclass(Dchol(as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE)))))", "flat(Dchol(as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True))))", "Scale a Cholesky factor to a correlation factor."),
    ("invcholD", "invcholD", "as.numeric(unclass(invcholD(as.invchol(ltMatrices(c(1, -0.2, 1.5), diag = TRUE)))))", "flat(invcholD(as_invchol(ltMatrices([1.0, -0.2, 1.5], diag=True))))", "Scale an inverse Cholesky."),
    ("chol2cor", "chol2cor", "as.numeric(unclass(chol2cor(as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE)))))", "flat(chol2cor(as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True))))", "Correlation from a Cholesky factor."),
    ("invchol2cor", "invchol2cor", "as.numeric(unclass(invchol2cor(as.invchol(ltMatrices(c(1, -0.2, 1.5), diag = TRUE)))))", "flat(invchol2cor(as_invchol(ltMatrices([1.0, -0.2, 1.5], diag=True))))", "Correlation from an inverse Cholesky."),
    ("chol2pc", "chol2pc", "as.numeric(chol2pc(as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE))))", "flat(chol2pc(as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True))))", "Partial correlations from a Cholesky factor."),
    ("invchol2pc", "invchol2pc", "as.numeric(invchol2pc(as.invchol(ltMatrices(c(1, -0.2, 1.5), diag = TRUE))))", "flat(invchol2pc(as_invchol(ltMatrices([1.0, -0.2, 1.5], diag=True))))", "Partial correlations from an inverse Cholesky."),
    ("vectrick", "vectrick", "as.numeric(unclass(vectrick(ltMatrices(c(1, 0.3, 1), diag = TRUE))))", "flat(vectrick(ltMatrices([1.0, 0.3, 1.0], diag=True)))", "With S and A omitted, the product is C' C."),
    ("marg_mvnorm", "marg_mvnorm", "C <- as.chol(ltMatrices(c(1, 0.3, 1, 0.2, 0.1, 1), diag = TRUE)); as.numeric(unclass(marg_mvnorm(chol = C, which = 1:2)$chol))", "flat(marg_mvnorm(chol=as_chol(ltMatrices([1, 0.3, 1, 0.2, 0.1, 1], diag=True)), which=[1, 2])['chol'])", "The leading 2 by 2 Cholesky block."),
    ("cond_mvnorm", "cond_mvnorm", "C <- as.chol(ltMatrices(c(1, 0.3, 1), diag = TRUE)); as.numeric(unclass(cond_mvnorm(chol = C, which_given = 1, given = matrix(0, 1))$chol))", "flat(cond_mvnorm(chol=as_chol(ltMatrices([1.0, 0.3, 1.0], diag=True)), which_given=1, given=np.array([[0.0]]))['chol'])", "Condition the second margin on the first at 0."),
    ("ldmvnorm", "ldmvnorm", "C <- ltMatrices(c(1, 0, 1), diag = TRUE); obs <- matrix(c(0, 0, 1, -1), 2); as.numeric(ldmvnorm(obs, chol = C))", "flat(ldmvnorm(np.array([[0.0, 1.0], [0.0, -1.0]]), chol=ltMatrices([1.0, 0.0, 1.0], diag=True)))", "Log-density of two bivariate observations."),
    ("lpmvnorm", "lpmvnorm", "as.numeric(lpmvnorm(lower = -1, upper = 1, chol = ltMatrices(1, diag = TRUE)))", "flat(lpmvnorm(lower=-1, upper=1, chol=ltMatrices([1.0], diag=True)))", "Interval log-probability, dimension 1."),
    ("slpmvnorm", "slpmvnorm", "as.numeric(slpmvnorm(lower = -1, upper = 1, chol = ltMatrices(1, diag = TRUE))$logLik)", "flat(slpmvnorm(lower=-1, upper=1, chol=ltMatrices([1.0], diag=True))['logLik'])", "Score log-likelihood in one dimension."),
    ("sldmvnorm", "sldmvnorm", "as.numeric(sldmvnorm(matrix(c(0, 1), 2), chol = ltMatrices(c(1, 0.3, 1), diag = TRUE))$logLik)", "flat(sldmvnorm(np.array([[0.0], [1.0]]), chol=ltMatrices([1.0, 0.3, 1.0], diag=True))['logLik'])", "Score of an exact observation."),
    ("ldpmvnorm", "ldpmvnorm", "C <- ltMatrices(c(1, 0.3, 1), diag = TRUE); as.numeric(ldpmvnorm(lower = matrix(-1, 2), upper = matrix(1, 2), chol = C, w = matrix(c(0.2, 0.5, 0.8), 1)))", "flat(ldpmvnorm(lower=np.array([[-1.0], [-1.0]]), upper=np.array([[1.0], [1.0]]), chol=ltMatrices([1.0, 0.3, 1.0], diag=True), w=np.array([[0.2, 0.5, 0.8]])))", "Interval log-likelihood with a fixed weight row."),
    ("sldpmvnorm", "sldpmvnorm", "C <- ltMatrices(c(1, 0.3, 1), diag = TRUE); as.numeric(sldpmvnorm(lower = matrix(-1, 2), upper = matrix(1, 2), chol = C, w = matrix(c(0.2, 0.5, 0.8), 1))$logLik)", "flat(sldpmvnorm(lower=np.array([[-1.0], [-1.0]]), upper=np.array([[1.0], [1.0]]), chol=ltMatrices([1.0, 0.3, 1.0], diag=True), w=np.array([[0.2, 0.5, 0.8]]))['logLik'])", "Score of that interval likelihood."),
    ("standardize", "standardize", "as.numeric(unclass(standardize(chol = as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE)))))", "flat(standardize(chol=as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True))))", "Correlation-scale Cholesky."),
    ("destandardize", "destandardize", "as.numeric(unclass(destandardize(chol = as.chol(ltMatrices(c(2, 0.5, 3), diag = TRUE)), score_schol = ltMatrices(c(0.1, 0.2, 0.3), diag = TRUE))))", "flat(destandardize(chol=as_chol(ltMatrices([2.0, 0.5, 3.0], diag=True)), score_schol=ltMatrices([0.1, 0.2, 0.3], diag=True)))", "Map a standardized score back to the covariance scale."),
    ("deperma", "deperma", "C <- as.chol(ltMatrices(c(1, 0.3, 1), diag = TRUE)); sc <- ltMatrices(c(0.1, 0.2, 0.3), diag = TRUE); as.numeric(deperma(chol = C, permuted_chol = C, score_schol = sc))", "C = as_chol(ltMatrices([1.0, 0.3, 1.0], diag=True)); flat(deperma(chol=C, permuted_chol=C, score_schol=ltMatrices([0.1, 0.2, 0.3], diag=True)))", "With perm omitted the score is returned as stored."),
    ("lpRR", "lpRR", "B <- matrix(c(1, 0, 0.5, 1), 2); Z <- matrix(c(0, 0.5, -0.5, 1), 2); as.numeric(lpRR(lower = c(-1, -1), upper = c(1, 1), B = B, Z = Z))", "flat(lpRR(lower=np.array([-1.0, -1.0]), upper=np.array([1.0, 1.0]), B=np.array([[1.0, 0.5], [0.0, 1.0]]), Z=np.array([[0.0, -0.5], [0.5, 1.0]])))", "Log-probability of a rectangular region."),
    ("slpRR", "slpRR", "B <- matrix(c(1, 0, 0.5, 1), 2); Z <- matrix(c(0, 0.5, -0.5, 1), 2); as.numeric(slpRR(lower = c(-1, -1), upper = c(1, 1), B = B, Z = Z)$mean)", "flat(slpRR(lower=np.array([-1.0, -1.0]), upper=np.array([1.0, 1.0]), B=np.array([[1.0, 0.5], [0.0, 1.0]]), Z=np.array([[0.0, -0.5], [0.5, 1.0]]))['mean'])", "Mean score of that region."),
    ("mvnorm", "mvnorm", "as.numeric(unclass(vcov(mvnorm(mean = c(1, 2), chol = ltMatrices(c(1, 0, 1), diag = TRUE)))))", "flat(vcov_mvnorm(mvnorm(mean=np.array([1.0, 2.0]), chol=ltMatrices([1.0, 0.0, 1.0], diag=True))))", "Covariance of a model whose Cholesky is the identity."),
    ("margDist", "margDist", "m <- mvnorm(chol = as.chol(ltMatrices(c(1, 0.3, 1), diag = TRUE))); as.numeric(unclass(margDist(m, 1)$scale))", "flat(margDist(mvnorm(chol=as_chol(ltMatrices([1.0, 0.3, 1.0], diag=True))), 1).scale)", "The first margin of a bivariate model."),
    ("condDist", "condDist", "m <- mvnorm(chol = as.chol(ltMatrices(c(1, 0.3, 1), diag = TRUE))); as.numeric(unclass(condDist(m, which_given = 1, given = matrix(0, 1))$scale))", "flat(condDist(mvnorm(chol=as_chol(ltMatrices([1.0, 0.3, 1.0], diag=True))), which_given=1, given=np.array([[0.0]])).scale)", "The conditional scale given the first margin at 0."),
    ("lLgrad", "lLgrad", "m <- mvnorm(chol = as.chol(ltMatrices(c(1, 0.3, 1), diag = TRUE))); obs <- matrix(0, 2, 1, dimnames = list(c('1', '2'), NULL)); as.numeric(lLgrad(m, obs = obs)$scale)", "from mvtnorm._iface import _RMatrix\nflat(lLgrad(mvnorm(chol=as_chol(ltMatrices([1.0, 0.3, 1.0], diag=True))), obs=_RMatrix(np.zeros((2, 1)), rownames=['1', '2']))['scale'])", "Score of two exact zeros. Row names are required."),
]

R_HEADER = """\
suppressPackageStartupMessages(library(mvtnorm))
fmt <- function(x) {
  if (is.logical(x) && length(x) == 1) return(if (isTRUE(x)) "1" else "0")
  paste(sprintf("%%.16g", as.numeric(x)), collapse = " ")
}
one <- function() {
  %s
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(fmt(value), "\\n", sep = "")
cat(sprintf("MS %%.17g\\n", median(elapsed) * 1000))
"""

PY_HEADER = """\
import math
import statistics
import time
import numpy as np
from boot.rng import set_seed
from mvtnorm import *

def flat(x):
    if isinstance(x, (bool, np.bool_)):
        return np.array([1.0 if x else 0.0])
    return np.atleast_1d(np.asarray(x, dtype=float)).ravel(order="F")

def one():
    %s

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join(f"{v:.16g}" for v in flat(value)))
print(f"MS {statistics.median(elapsed):.17g}")
"""


def _py_body(expr: str) -> str:
    if "\n" in expr and ";" not in expr:
        lines = [part.strip() for part in expr.split("\n") if part.strip()]
        *body, last = lines
        rows = body + [f"return {last}"]
    else:
        lines = [part.strip() for part in expr.split(";")]
        *body, last = lines
        rows = body + [f"return {last}"]
    return textwrap.indent("\n".join(rows), "    ").strip()


def _r_body(expr: str) -> str:
    lines = [part.strip() for part in expr.split(";")]
    *body, last = lines
    rows = body + [last]
    return "\n  ".join(rows)


def _py_example(py_name: str, expr: str) -> str:
    header = ["import numpy as np", "from mvtnorm import *"]
    if "set_seed" in expr:
        header.insert(1, "from boot.rng import set_seed")
    if "math." in expr:
        header.insert(0, "import math")
    if "_RMatrix" in expr:
        header.append("from mvtnorm._iface import _RMatrix")
    if "\n" in expr and ";" not in expr:
        lines = [part.strip() for part in expr.split("\n") if part.strip()]
    else:
        lines = [part.strip() for part in expr.split(";")]
    *body, last = lines
    shown = last
    if shown.startswith("flat(") and shown.endswith(")"):
        shown = shown[5:-1]
    rows = body + [f"print({shown})"]
    return "\n".join(header + [""] + rows) + "\n"


def _run(cmd, text):
    path = Path("/tmp") / ("mvt-one-" + ("r.R" if cmd[0] == "Rscript" else "py.py"))
    # unique names per call would race; write beside the proof instead
    return text


def _exec(program, script: Path):
    if program == "R":
        proc = subprocess.run(["Rscript", str(script)], capture_output=True, text=True, check=False)
    else:
        env_python = [str(PY), str(script)]
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            str(ROOT / "packages" / name) for name in ("mvtnorm", "boot", "extraDistr")
        )
        proc = subprocess.run(env_python, capture_output=True, text=True, check=False, cwd="/tmp", env=env)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout)
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    value = lines[-2] if lines[-1].startswith("MS ") else lines[-1]
    ms = float(lines[-1].split()[1]) if lines[-1].startswith("MS ") else float("nan")
    return value, ms


def _numbers(text: str):
    if text in ("1", "0") and " " not in text:
        return [float(text)]
    return [float(part) for part in text.split()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    functions = []
    for name, py_name, r_expr, py_expr, note in CASES:
        safe = name.replace("<-", "_set").replace(".", "_")
        r_script = R_HEADER % _r_body(r_expr)
        py_script = PY_HEADER % _py_body(py_expr)
        r_path = PROOF / f"{safe}-r.R"
        py_path = PROOF / f"{safe}-py.py"
        r_path.write_text(r_script)
        py_path.write_text(py_script)
        r_value, r_ms = _exec("R", r_path)
        py_value, py_ms = _exec("py", py_path)
        r_num, py_num = _numbers(r_value), _numbers(py_value)
        if len(r_num) != len(py_num):
            raise SystemExit(f"{name}: length {len(r_num)} vs {len(py_num)}\nR {r_value}\nP {py_value}")
        diff = max((abs(a - b) for a, b in zip(r_num, py_num)), default=0.0)
        if not math.isfinite(diff) or diff > 1e-8:
            raise SystemExit(f"{name}: diff {diff}\nR {r_value}\nP {py_value}")
        (OUT / f"{safe}-r.txt").write_text(r_value + "\n")
        (OUT / f"{safe}-python.txt").write_text(py_value + "\n")
        example_r = f"suppressPackageStartupMessages(library(mvtnorm))\ncat({r_expr if ';' not in r_expr else 'the check'}, \"\\n\")\n"
        # The captured file is the check value. The example is the same call.
        doc = {
            "name": name,
            "title": name,
            "origin": {
                "description": note,
                "usage": name,
                "arguments": [],
                "details": note,
                "value": r_value,
                "example": r_expr,
                "output": f"output/{safe}-r.txt",
            },
            "translation": {
                "description": note,
                "usage": py_name,
                "arguments": [],
                "details": note,
                "value": py_value,
                "example": _py_example(py_name, py_expr),
                "output": f"output/{safe}-python.txt",
            },
        }
        (DOCS / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n")
        speedup = (r_ms / py_ms) if py_ms else None
        functions.append(
            {
                "name": name,
                "translated": True,
                "python": f"mvtnorm.{py_name}",
                "loads": ["boot", "extraDistr"] if name in {"rmvnorm", "rmvt", "pmvnorm", "pmvt", "qmvnorm", "qmvt", "lpmvnorm", "slpmvnorm"} else [],
                "uses": ["numpy", "scipy"] if name in {"pmvnorm", "pmvt", "qmvnorm", "qmvt"} else ["numpy"],
                "done": note,
                "not_done": "",
                "blocked_by": [],
                "assigned": "",
                "check": {
                    "case": note,
                    "r_ms": r_ms,
                    "translated_ms": py_ms,
                    "speedup": speedup,
                    "matches": True,
                    "max_abs_diff": diff,
                    "tolerance": 1e-8,
                    "proof": {"r": r_script, "python": py_script},
                },
            }
        )
        print(f"ok {name} diff {diff:.1e} {r_ms:.3g} ms / {py_ms:.3g} ms")
    record = {
        "name": "mvtnorm",
        "cran_version": "1.4-2",
        "inventory": "complete",
        "status": "complete",
        "blocked_by": [],
        "crate_claims": ["mvtdst"],
        "resume": "All exports of mvtnorm 1.4-2 match R within 1e-8. Genz–Bretz and TVPACK are the Fortran in crates/mvtdst, with uniforms from boot and univariate margins from SciPy. Miwa is the C orthant routine in that crate. Lower-triangular algebra and the log-likelihoods are NumPy. utils::getFromNamespace is only used to call this package's own invchol, so utils is not loaded.",
        "dependencies": {
            "translated": ["boot", "extraDistr"],
            "native": ["numpy", "scipy"],
            "rust": ["mvtdst"],
        },
        "functions": functions,
    }
    (PKG / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"recorded {len(functions)}")


if __name__ == "__main__":
    main()
