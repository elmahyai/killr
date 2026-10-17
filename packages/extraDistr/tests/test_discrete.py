"""extraDistr discrete families against R, tolerance 1e-8."""

import math
import os
import subprocess
import tempfile
import warnings

import numpy as np
from boot.rng import set_seed

from extradistr import discrete

TOL = 1e-8

# name, R expression, Python expression, random draw
CASES = [
    ('dbern', 'dbern(c(0, 1, 2), 0.3)', 'dbern([0, 1, 2], 0.3)', False),
    ('pbern', 'pbern(c(-1, 0, 0.4, 1, 2), 0.3)', 'pbern([-1, 0, 0.4, 1, 2], 0.3)', False),
    ('qbern', 'qbern(c(0, 0.2, 0.5, 0.7, 1), 0.3)', 'qbern([0, 0.2, 0.5, 0.7, 1], 0.3)', False),
    ('rbern', 'rbern(4, 0.3)', 'rbern(4, 0.3)', True),
    ('dbbinom', 'dbbinom(0:4, 4, 1, 1)', 'dbbinom(list(range(5)), 4, 1, 1)', False),
    ('pbbinom', 'pbbinom(0:4, 4, 2, 3)', 'pbbinom(list(range(5)), 4, 2, 3)', False),
    ('rbbinom', 'rbbinom(4, 4, 1, 1)', 'rbbinom(4, 4, 1, 1)', True),
    ('dbnbinom', 'dbnbinom(0:5, 3, 2, 4)', 'dbnbinom(list(range(6)), 3, 2, 4)', False),
    ('pbnbinom', 'pbnbinom(0:5, 3, 2, 4)', 'pbnbinom(list(range(6)), 3, 2, 4)', False),
    ('rbnbinom', 'rbnbinom(4, 3, 2, 4)', 'rbnbinom(4, 3, 2, 4)', True),
    ('ddlaplace', 'ddlaplace(-2:2, 0, 0.4)', 'ddlaplace(list(range(-2, 3)), 0, 0.4)', False),
    ('pdlaplace', 'pdlaplace(c(-1.2, 0, 1.5), 0.2, 0.5)', 'pdlaplace([-1.2, 0, 1.5], 0.2, 0.5)', False),
    ('rdlaplace', 'rdlaplace(4, 0, 0.4)', 'rdlaplace(4, 0, 0.4)', True),
    ('ddweibull', 'ddweibull(0:5, 0.4, 1.3)', 'ddweibull(list(range(6)), 0.4, 1.3)', False),
    ('pdweibull', 'pdweibull(c(-1, 0, 1.2, 3), 0.4, 1.3)', 'pdweibull([-1, 0, 1.2, 3], 0.4, 1.3)', False),
    ('qdweibull', 'qdweibull(c(0, 0.2, 0.5, 0.9), 0.4, 1.3)', 'qdweibull([0, 0.2, 0.5, 0.9], 0.4, 1.3)', False),
    ('rdweibull', 'rdweibull(4, 0.4, 1.2)', 'rdweibull(4, 0.4, 1.2)', True),
    ('ddunif', 'ddunif(c(0, 2, 3.5, 5, 6), 2, 5)', 'ddunif([0, 2, 3.5, 5, 6], 2, 5)', False),
    ('pdunif', 'pdunif(c(1, 2.3, 5, 6), 2, 5)', 'pdunif([1, 2.3, 5, 6], 2, 5)', False),
    ('qdunif', 'qdunif(c(0, 0.1, 0.5, 1), 2, 5)', 'qdunif([0, 0.1, 0.5, 1], 2, 5)', False),
    ('rdunif', 'rdunif(4, 1, 6)', 'rdunif(4, 1, 6)', True),
    ('dlgser', 'dlgser(1:5, 0.4)', 'dlgser(list(range(1, 6)), 0.4)', False),
    ('plgser', 'plgser(c(0, 1, 2.4, 5), 0.5)', 'plgser([0, 1, 2.4, 5], 0.5)', False),
    ('qlgser', 'qlgser(c(0, 0.2, 0.5, 0.9), 0.4)', 'qlgser([0, 0.2, 0.5, 0.9], 0.4)', False),
    ('rlgser', 'rlgser(4, 0.6)', 'rlgser(4, 0.6)', True),
    ('dcat', 'dcat(1:3, c(0.2, 0.3, 0.5))', 'dcat([1, 2, 3], [0.2, 0.3, 0.5])', False),
    ('pcat', 'pcat(c(0, 1, 1.7, 3, 4), c(0.2, 0.3, 0.5))', 'pcat([0, 1, 1.7, 3, 4], [0.2, 0.3, 0.5])', False),
    ('qcat', 'qcat(c(0.1, 0.5, 0.9), c(0.2, 0.3, 0.5))', 'qcat([0.1, 0.5, 0.9], [0.2, 0.3, 0.5])', False),
    ('rcat', 'rcat(4, c(0.2, 0.3, 0.5))', 'rcat(4, [0.2, 0.3, 0.5])', True),
    ('rcatlp', 'rcatlp(4, log(c(0.1, 0.2, 0.7)))', 'rcatlp(4, [math.log(0.1), math.log(0.2), math.log(0.7)])', True),
    ('dskellam', 'dskellam(-2:2, 1.5, 0.7)', 'dskellam(list(range(-2, 3)), 1.5, 0.7)', False),
    ('rskellam', 'rskellam(4, 1.5, 0.7)', 'rskellam(4, 1.5, 0.7)', True),
    ('dzib', 'dzib(0:4, 5, 0.4, 0.2)', 'dzib(list(range(5)), 5, 0.4, 0.2)', False),
    ('pzib', 'pzib(0:5, 5, 0.4, 0.2)', 'pzib(list(range(6)), 5, 0.4, 0.2)', False),
    ('qzib', 'qzib(c(0.1, 0.3, 0.8), 5, 0.4, 0.2)', 'qzib([0.1, 0.3, 0.8], 5, 0.4, 0.2)', False),
    ('rzib', 'rzib(4, 5, 0.4, 0.2)', 'rzib(4, 5, 0.4, 0.2)', True),
    ('dzip', 'dzip(0:4, 2, 0.3)', 'dzip(list(range(5)), 2, 0.3)', False),
    ('pzip', 'pzip(0:4, 2, 0.3)', 'pzip(list(range(5)), 2, 0.3)', False),
    ('qzip', 'qzip(c(0.1, 0.5, 0.9), 2, 0.3)', 'qzip([0.1, 0.5, 0.9], 2, 0.3)', False),
    ('rzip', 'rzip(4, 2, 0.3)', 'rzip(4, 2, 0.3)', True),
    ('dzinb', 'dzinb(0:4, 2, 0.4, 0.25)', 'dzinb(list(range(5)), 2, 0.4, 0.25)', False),
    ('pzinb', 'pzinb(0:4, 2, 0.4, 0.25)', 'pzinb(list(range(5)), 2, 0.4, 0.25)', False),
    ('qzinb', 'qzinb(c(0.1, 0.4, 0.8), 2, 0.4, 0.25)', 'qzinb([0.1, 0.4, 0.8], 2, 0.4, 0.25)', False),
    ('rzinb', 'rzinb(4, 2, 0.4, 0.25)', 'rzinb(4, 2, 0.4, 0.25)', True),
    ('dtbinom', 'dtbinom(0:6, 6, 0.4, 1, 4)', 'dtbinom(list(range(7)), 6, 0.4, 1, 4)', False),
    ('ptbinom', 'ptbinom(0:6, 6, 0.4, 1, 4)', 'ptbinom(list(range(7)), 6, 0.4, 1, 4)', False),
    ('qtbinom', 'qtbinom(c(0, 0.2, 0.5, 1), 6, 0.4, 1, 4)', 'qtbinom([0, 0.2, 0.5, 1], 6, 0.4, 1, 4)', False),
    ('rtbinom', 'rtbinom(4, 10, 0.4, 1, 8)', 'rtbinom(4, 10, 0.4, 1, 8)', True),
    ('dtpois', 'dtpois(0:6, 2, 1, 5)', 'dtpois(list(range(7)), 2, 1, 5)', False),
    ('ptpois', 'ptpois(0:6, 2, 1, 5)', 'ptpois(list(range(7)), 2, 1, 5)', False),
    ('qtpois', 'qtpois(c(0.1, 0.5, 0.9), 2, 1, 5)', 'qtpois([0.1, 0.5, 0.9], 2, 1, 5)', False),
    ('rtpois', 'rtpois(4, 3, 0, 6)', 'rtpois(4, 3, 0, 6)', True),
    ('dnhyper', 'dnhyper(2:6, 5, 8, 2)', 'dnhyper(list(range(2, 7)), 5, 8, 2)', False),
    ('pnhyper', 'pnhyper(2:7, 5, 8, 2)', 'pnhyper(list(range(2, 8)), 5, 8, 2)', False),
    ('qnhyper', 'qnhyper(c(0.1, 0.5, 0.9), 5, 8, 2)', 'qnhyper([0.1, 0.5, 0.9], 5, 8, 2)', False),
    ('rnhyper', 'rnhyper(4, 5, 8, 2)', 'rnhyper(4, 5, 8, 2)', True),
    ('dmnom', 'dmnom(c(1, 2, 3), 6, c(0.2, 0.3, 0.5))', 'dmnom([1, 2, 3], 6, [0.2, 0.3, 0.5])', False),
    ('rmnom', 'rmnom(4, 6, c(0.2, 0.3, 0.5))', 'rmnom(4, 6, [0.2, 0.3, 0.5])', True),
    ('ddirmnom', 'ddirmnom(c(1, 2, 3), 6, c(0.5, 1, 1.5))', 'ddirmnom([1, 2, 3], 6, [0.5, 1, 1.5])', False),
    ('rdirmnom', 'rdirmnom(4, 6, c(0.5, 1, 1.5))', 'rdirmnom(4, 6, [0.5, 1, 1.5])', True),
    ('dmvhyper', 'dmvhyper(c(1, 2, 1), c(3, 4, 2), 4)', 'dmvhyper([1, 2, 1], [3, 4, 2], 4)', False),
    ('rmvhyper', 'rmvhyper(4, c(3, 4, 2), 4)', 'rmvhyper(4, [3, 4, 2], 4)', True),
    ('dgpois', 'dgpois(0:4, 2, 1.5)', 'dgpois(list(range(5)), 2, 1.5)', False),
    ('pgpois', 'pgpois(0:4, 2, 1.5)', 'pgpois(list(range(5)), 2, 1.5)', False),
    ('rgpois', 'rgpois(4, 2, 1.5)', 'rgpois(4, 2, 1.5)', True),
    ('ddgamma', 'ddgamma(0:4, 2, 1)', 'ddgamma(list(range(5)), 2, 1)', False),
    ('pdgamma', 'pdgamma(c(-0.2, 0, 1.5, 3), 2, 1)', 'pdgamma([-0.2, 0, 1.5, 3], 2, 1)', False),
    ('rdgamma', 'rdgamma(4, 2, 1)', 'rdgamma(4, 2, 1)', True),
    ('ddnorm', 'ddnorm(c(-1, 0, 1, 2), 0.5, 1.2)', 'ddnorm([-1, 0, 1, 2], 0.5, 1.2)', False),
    ('pdnorm', 'pdnorm(c(-1.2, 0, 1.7), 0.5, 1.2)', 'pdnorm([-1.2, 0, 1.7], 0.5, 1.2)', False),
    ('rdnorm', 'rdnorm(4, 1.5, 0.8)', 'rdnorm(4, 1.5, 0.8)', True),
    ('rsign', 'rsign(4)', 'rsign(4)', True),
]


def _parse(text):
    values = []
    for part in text.strip().split(','):
        token = part.strip()
        if token in {"NA", "NaN", "nan"}:
            values.append(math.nan)
        elif token in {"Inf", "inf"}:
            values.append(math.inf)
        elif token in {"-Inf", "-inf"}:
            values.append(-math.inf)
        else:
            values.append(float(token))
    return np.asarray(values, dtype=float)


def _flatten(value):
    return np.ravel(np.asarray(value, dtype=float), order="C")


def _r_lines():
    lines = [
        "suppressPackageStartupMessages(library(extraDistr))",
        "fmt <- function(x) {",
        "  if (is.matrix(x)) x <- as.vector(t(x))",
        "  paste(sprintf('%.17g', as.numeric(x)), collapse=\",\")",
        "}",
    ]
    for name, expr, _py, random in CASES:
        if random:
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
        if not line.strip():
            continue
        name, rest = line.split("\t", 1)
        found[name] = rest
    missing = [name for name, *_ in CASES if name not in found]
    if missing:
        raise RuntimeError(completed.stderr or "missing " + ",".join(missing))
    return found


def _python(expr, random):
    if random:
        set_seed(1)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        value = eval(expr, {"math": math, "np": np}, discrete.__dict__)
    return _flatten(value)


def test_discrete_matches_r():
    expected = _r_lines()
    failures = []
    for name, _expr, py, random in CASES:
        got = _python(py, random)
        want = _parse(expected[name])
        if got.shape != want.shape or not np.allclose(
            got, want, rtol=TOL, atol=TOL, equal_nan=True
        ):
            failures.append(f"{name}\n  py {got}\n  R  {want}")
    assert not failures, "\n".join(failures)
