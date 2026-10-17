"""extraDistr multivariate families against R, tolerance 1e-8."""

import os
import subprocess
import tempfile
import warnings

import numpy as np
import pytest
from boot.rng import set_seed

from extradistr.multivariate import (
    dbvnorm,
    dbvpois,
    ddirichlet,
    dmixnorm,
    dmixpois,
    pmixnorm,
    pmixpois,
    rbvnorm,
    rbvpois,
    rdirichlet,
    rmixnorm,
    rmixpois,
)

TOL = 1e-8


def _parse(text):
    text = text.strip()
    if text == "":
        return np.asarray([], dtype=float)
    values = []
    for part in text.split(","):
        token = part.strip()
        if token in {"NA", "NaN", "nan"}:
            values.append(np.nan)
        elif token in {"Inf", "inf"}:
            values.append(np.inf)
        elif token in {"-Inf", "-inf"}:
            values.append(-np.inf)
        else:
            values.append(float(token))
    return np.asarray(values, dtype=float)


def _flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")


def _r_batch(cases):
    lines = [
        "suppressPackageStartupMessages(library(extraDistr))",
        "fmt <- function(x) {",
        "  if (is.matrix(x)) x <- as.vector(t(x))",
        "  x <- as.vector(x)",
        "  if (length(x) == 0) return('')",
        "  paste(sprintf('%.17g', x), collapse=',')",
        "}",
    ]
    for name, expr, seed in cases:
        if seed:
            lines.append("set.seed(1)")
        lines.append(f'cat("{name}\\t", fmt({expr}), "\\n", sep="")')
    script = "\n".join(lines)
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        completed = subprocess.run(
            ["Rscript", "--vanilla", path],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(path)
    found = {}
    for line in completed.stdout.splitlines():
        name, _, payload = line.partition("\t")
        found[name] = _parse(payload)
    return found


def _assert_close(name, got, expected):
    got = _flatten(got)
    if got.shape != expected.shape:
        raise AssertionError(f"{name}: length {got.shape} != {expected.shape}")
    if got.size == 0:
        return
    if not np.allclose(got, expected, rtol=TOL, atol=TOL, equal_nan=True):
        gap = np.nanmax(np.abs(np.asarray(got, dtype=float) - expected))
        raise AssertionError(f"{name}: max abs diff {gap}\npython {got}\nR {expected}")


CASES = [
    (
        "ddirichlet",
        "ddirichlet(matrix(c(0.2,0.3,0.5,0.1,0.2,0.7), ncol=3, byrow=TRUE), matrix(c(1,2,3,0.5,0.5,0.5), ncol=3, byrow=TRUE))",
        False,
        lambda: ddirichlet(
            [[0.2, 0.3, 0.5], [0.1, 0.2, 0.7]],
            [[1.0, 2.0, 3.0], [0.5, 0.5, 0.5]],
        ),
    ),
    (
        "ddirichlet_log",
        "ddirichlet(matrix(c(0.2,0.3,0.5,0.1,0.2,0.7), ncol=3, byrow=TRUE), matrix(c(1,2,3,0.5,0.5,0.5), ncol=3, byrow=TRUE), log=TRUE)",
        False,
        lambda: ddirichlet(
            [[0.2, 0.3, 0.5], [0.1, 0.2, 0.7]],
            [[1.0, 2.0, 3.0], [0.5, 0.5, 0.5]],
            log=True,
        ),
    ),
    (
        "ddirichlet_vec",
        "ddirichlet(matrix(c(0.2,0.3,0.5,0.1,0.2,0.7), ncol=3, byrow=TRUE), c(1,2,3))",
        False,
        lambda: ddirichlet([[0.2, 0.3, 0.5], [0.1, 0.2, 0.7]], [1, 2, 3]),
    ),
    (
        "ddirichlet_extra",
        "ddirichlet(matrix(c(0.2,0.3,0.5), nrow=1), matrix(c(1,2,3,9), nrow=1))",
        False,
        lambda: ddirichlet([[0.2, 0.3, 0.5]], [[1, 2, 3, 9]]),
    ),
    (
        "ddirichlet_off",
        "ddirichlet(matrix(c(0.2,0.2,0.2), nrow=1), c(1,2,3))",
        False,
        lambda: ddirichlet([[0.2, 0.2, 0.2]], [1, 2, 3]),
    ),
    (
        "ddirichlet_out",
        "ddirichlet(matrix(c(1.2,0.3,0.5), nrow=1), c(1,2,3))",
        False,
        lambda: ddirichlet([[1.2, 0.3, 0.5]], [1, 2, 3]),
    ),
    (
        "ddirichlet_zero",
        "ddirichlet(matrix(c(0,0.5,0.5), nrow=1), c(1,2,2))",
        False,
        lambda: ddirichlet([[0, 0.5, 0.5]], [1, 2, 2]),
    ),
    (
        "ddirichlet_sing",
        "ddirichlet(matrix(c(0,1), nrow=1), c(0.5,0.5))",
        False,
        lambda: ddirichlet([[0, 1]], [0.5, 0.5]),
    ),
    (
        "ddirichlet_empty",
        "ddirichlet(matrix(numeric(0), ncol=3), c(1,1,1))",
        False,
        lambda: ddirichlet(np.zeros((0, 3)), [1, 1, 1]),
    ),
    (
        "dbvnorm",
        "dbvnorm(c(-1,0,1.5), c(0.2,-0.3,0.7), mean1=c(0,1), mean2=0, sd1=1, sd2=c(1,1.5), cor=c(0.2,-0.4))",
        False,
        lambda: dbvnorm(
            [-1, 0, 1.5],
            [0.2, -0.3, 0.7],
            mean1=[0, 1],
            mean2=0,
            sd1=1,
            sd2=[1, 1.5],
            cor=[0.2, -0.4],
        ),
    ),
    (
        "dbvnorm_log",
        "dbvnorm(cbind(c(-1,0,1), c(0.5,0,-0.5)), cor=-0.25, log=TRUE)",
        False,
        lambda: dbvnorm(
            np.array([[-1.0, 0.5], [0.0, 0.0], [1.0, -0.5]]),
            cor=-0.25,
            log=True,
        ),
    ),
    (
        "dbvnorm_recycle",
        "dbvnorm(c(0,1), c(0,0), mean1=c(0,1,-1), cor=c(0.2,-0.3,0.5))",
        False,
        lambda: dbvnorm([0, 1], [0, 0], mean1=[0, 1, -1], cor=[0.2, -0.3, 0.5]),
    ),
    (
        "dbvnorm_empty",
        "dbvnorm(numeric(0), c(1,2), cor=0)",
        False,
        lambda: dbvnorm([], [1, 2], cor=0),
    ),
    (
        "dbvpois",
        "dbvpois(c(0,1,2,3), c(1,1,0,2), a=c(1,1.5), b=0.8, c=c(0.2,0.5))",
        False,
        lambda: dbvpois([0, 1, 2, 3], [1, 1, 0, 2], [1, 1.5], 0.8, [0.2, 0.5]),
    ),
    (
        "dbvpois_log",
        "dbvpois(c(0,1,2,3), c(1,1,0,2), a=c(1,1.5), b=0.8, c=c(0.2,0.5), log=TRUE)",
        False,
        lambda: dbvpois(
            [0, 1, 2, 3], [1, 1, 0, 2], [1, 1.5], 0.8, [0.2, 0.5], log=True
        ),
    ),
    (
        "dbvpois_nonint",
        "suppressWarnings(dbvpois(1.5, 1, a=1, b=1, c=0.2))",
        False,
        lambda: dbvpois(1.5, 1, 1, 1, 0.2),
    ),
    (
        "dbvpois_c0",
        "dbvpois(1, 1, a=1, b=1, c=0)",
        False,
        lambda: dbvpois(1, 1, 1, 1, 0),
    ),
    (
        "dbvpois_big",
        "dbvpois(c(10,8), c(8,12), a=2, b=3, c=1)",
        False,
        lambda: dbvpois([10, 8], [8, 12], 2, 3, 1),
    ),
    (
        "dmixnorm",
        "dmixnorm(c(-1,0,2,5), c(0,3), c(1,1.5), c(0.4,0.6))",
        False,
        lambda: dmixnorm([-1, 0, 2, 5], [0, 3], [1, 1.5], [0.4, 0.6]),
    ),
    (
        "dmixnorm_log",
        "dmixnorm(c(-1,0,2,5), c(0,3), c(1,1.5), c(0.4,0.6), log=TRUE)",
        False,
        lambda: dmixnorm([-1, 0, 2, 5], [0, 3], [1, 1.5], [0.4, 0.6], log=True),
    ),
    (
        "dmixnorm_rows",
        "dmixnorm(c(0,1,0.5), matrix(c(0,1,2,3), ncol=2, byrow=TRUE), c(1,1), matrix(c(0.2,0.8,0.6,0.4), ncol=2, byrow=TRUE))",
        False,
        lambda: dmixnorm(
            [0, 1, 0.5],
            [[0.0, 1.0], [2.0, 3.0]],
            [1, 1],
            [[0.2, 0.8], [0.6, 0.4]],
        ),
    ),
    (
        "dmixnorm_one",
        "dmixnorm(c(-1,0,1), 0, 1, 1)",
        False,
        lambda: dmixnorm([-1, 0, 1], 0, 1, 1),
    ),
    (
        "dmixnorm_bad",
        "suppressWarnings(dmixnorm(c(0,1), c(0,1), c(1,1), c(-0.2,1.2)))",
        False,
        lambda: dmixnorm([0, 1], [0, 1], [1, 1], [-0.2, 1.2]),
    ),
    (
        "pmixnorm",
        "pmixnorm(c(-2,0,1,4), c(0,3), c(1,1.5), c(0.4,0.6))",
        False,
        lambda: pmixnorm([-2, 0, 1, 4], [0, 3], [1, 1.5], [0.4, 0.6]),
    ),
    (
        "pmixnorm_upper",
        "pmixnorm(c(-2,0,1,4), c(0,3), c(1,1.5), c(0.4,0.6), lower.tail=FALSE, log.p=TRUE)",
        False,
        lambda: pmixnorm(
            [-2, 0, 1, 4], [0, 3], [1, 1.5], [0.4, 0.6], lower_tail=False, log_p=True
        ),
    ),
    (
        "pmixnorm_inf",
        "pmixnorm(c(-Inf, Inf), c(0,1), c(1,1), c(0.5,0.5))",
        False,
        lambda: pmixnorm([-np.inf, np.inf], [0, 1], [1, 1], [0.5, 0.5]),
    ),
    (
        "pmixnorm_sd0",
        "pmixnorm(c(-1,0,1), c(0,2), c(0,1), c(0.5,0.5))",
        False,
        lambda: pmixnorm([-1, 0, 1], [0, 2], [0, 1], [0.5, 0.5]),
    ),
    (
        "dmixpois",
        "dmixpois(c(0,1,3,8), c(1,5), c(0.3,0.7))",
        False,
        lambda: dmixpois([0, 1, 3, 8], [1, 5], [0.3, 0.7]),
    ),
    (
        "dmixpois_log",
        "dmixpois(c(0,1,3,8), c(1,5), c(0.3,0.7), log=TRUE)",
        False,
        lambda: dmixpois([0, 1, 3, 8], [1, 5], [0.3, 0.7], log=True),
    ),
    (
        "dmixpois_nonint",
        "suppressWarnings(dmixpois(1.5, c(1,2), c(0.5,0.5)))",
        False,
        lambda: dmixpois(1.5, [1, 2], [0.5, 0.5]),
    ),
    (
        "dmixpois_one",
        "dmixpois(0:5, 2, 1)",
        False,
        lambda: dmixpois(list(range(6)), 2, 1),
    ),
    (
        "dmixpois_tail",
        "dmixpois(c(0,10,20,30), 15, 1)",
        False,
        lambda: dmixpois([0, 10, 20, 30], 15, 1),
    ),
    (
        "pmixpois",
        "pmixpois(c(0,2,5,10), c(1,5), c(0.3,0.7))",
        False,
        lambda: pmixpois([0, 2, 5, 10], [1, 5], [0.3, 0.7]),
    ),
    (
        "pmixpois_upper",
        "pmixpois(c(0,2,5,10), c(1,5), c(0.3,0.7), lower.tail=FALSE, log.p=TRUE)",
        False,
        lambda: pmixpois([0, 2, 5, 10], [1, 5], [0.3, 0.7], lower_tail=False, log_p=True),
    ),
    (
        "pmixpois_half",
        "pmixpois(c(1, 1.5), c(1,2), c(0.5,0.5))",
        False,
        lambda: pmixpois([1, 1.5], [1, 2], [0.5, 0.5]),
    ),
    (
        "pmixpois_neg",
        "pmixpois(c(-1,-0.2,0), c(1,2), c(0.5,0.5))",
        False,
        lambda: pmixpois([-1, -0.2, 0], [1, 2], [0.5, 0.5]),
    ),
    (
        "rdirichlet",
        "rdirichlet(4, matrix(c(1,1,1,2,3,4), ncol=3, byrow=TRUE))",
        True,
        lambda: rdirichlet(4, [[1.0, 1, 1], [2, 3, 4]]),
    ),
    (
        "rdirichlet_vec",
        "rdirichlet(3, c(1,1,1,1))",
        True,
        lambda: rdirichlet(3, [1, 1, 1, 1]),
    ),
    (
        "rdirichlet_bad",
        "suppressWarnings(rdirichlet(3, matrix(c(1,1,1,-1,2,2,1,2,3), ncol=3, byrow=TRUE)))",
        True,
        lambda: rdirichlet(3, [[1.0, 1, 1], [-1, 2, 2], [1, 2, 3]]),
    ),
    (
        "rbvnorm",
        "rbvnorm(4, mean1=c(0,1), mean2=c(0,-1), sd1=c(1,2), sd2=1, cor=c(0,0.5))",
        True,
        lambda: rbvnorm(4, mean1=[0, 1], mean2=[0, -1], sd1=[1, 2], sd2=1, cor=[0, 0.5]),
    ),
    (
        "rbvnorm_one",
        "rbvnorm(3, cor=1)",
        True,
        lambda: rbvnorm(3, cor=1),
    ),
    (
        "rbvpois",
        "rbvpois(4, a=c(1,0.5), b=1.2, c=c(0.3,0.1))",
        True,
        lambda: rbvpois(4, [1, 0.5], 1.2, [0.3, 0.1]),
    ),
    (
        "rbvpois_bad",
        "suppressWarnings(rbvpois(3, a=c(1,-1,0.5), b=1, c=0.2))",
        True,
        lambda: rbvpois(3, [1, -1, 0.5], 1, 0.2),
    ),
    (
        "rmixnorm",
        "rmixnorm(4, c(0,4), c(1,1), c(0.25,0.75))",
        True,
        lambda: rmixnorm(4, [0, 4], [1, 1], [0.25, 0.75]),
    ),
    (
        "rmixnorm_sd0",
        "rmixnorm(6, c(0,5), c(0,1), c(0.5,0.5))",
        True,
        lambda: rmixnorm(6, [0, 5], [0, 1], [0.5, 0.5]),
    ),
    (
        "rmixnorm_bad",
        "suppressWarnings(rmixnorm(3, matrix(c(0,1,0,1,0,1), ncol=2, byrow=TRUE), matrix(c(1,1,-1,1,1,1), ncol=2, byrow=TRUE), c(0.5,0.5)))",
        True,
        lambda: rmixnorm(
            3,
            [[0.0, 1], [0, 1], [0, 1]],
            [[1.0, 1], [-1, 1], [1, 1]],
            [0.5, 0.5],
        ),
    ),
    (
        "rmixpois",
        "rmixpois(5, c(1,4), c(0.25,0.75))",
        True,
        lambda: rmixpois(5, [1, 4], [0.25, 0.75]),
    ),
    (
        "rmixpois_n",
        "rmixpois(c(7,8,9), c(1,4), c(0.25,0.75))",
        True,
        lambda: rmixpois([7, 8, 9], [1, 4], [0.25, 0.75]),
    ),
]


def test_matches_r():
    expected = _r_batch([(name, expr, seed) for name, expr, seed, _fn in CASES])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, _expr, seed, fn in CASES:
            if seed:
                set_seed(1)
            _assert_close(name, fn(), expected[name])


def test_shapes():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        set_seed(1)
        assert rdirichlet(4, [1, 1, 1]).shape == (4, 3)
        set_seed(1)
        assert rbvnorm(3, cor=0.2).shape == (3, 2)
        set_seed(1)
        assert rbvpois(3, 1, 1, 0.2).shape == (3, 2)
        assert rmixnorm(5, [0, 1], [1, 1], [0.5, 0.5]).shape == (5,)
        assert rmixpois(5, [1, 2], [0.5, 0.5]).shape == (5,)


def test_errors():
    with pytest.raises(ValueError, match="columns in alpha"):
        ddirichlet([0.5, 0.5], [1])
    with pytest.raises(ValueError, match="number of columns in x"):
        ddirichlet([[0.2, 0.3, 0.5, 0.1]], [1, 2])
    with pytest.raises(ValueError, match="lengths of x and y differ"):
        dbvnorm([1, 2], [1], cor=0)
    with pytest.raises(ValueError, match="two-column matrix"):
        dbvnorm([1, 2], cor=0)
    with pytest.raises(ValueError, match="do not match"):
        dmixnorm([0, 1], [0, 1], [1], [0.5, 0.5])
    with pytest.raises(ValueError, match="lambda and alpha"):
        dmixpois([0, 1], [1, 2], [1])
    with pytest.raises(TypeError, match="required"):
        dbvpois([0, 1], [0, 1], 1, 1)
