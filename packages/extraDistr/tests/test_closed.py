"""One comparison per closed-form export against extraDistr 1.10.0.5."""

import math
import subprocess

import numpy as np

from boot.rng import set_seed
from extradistr import closed

# Each export is called once. Random draws use set.seed(1) / set_seed(1).
CASES = [
    ("dlaplace", "dlaplace(c(-2, -0.5, 0.5, 3), 0.5, 1.5)", "dlaplace([-2, -0.5, 0.5, 3], 0.5, 1.5)", False),
    ("plaplace", "plaplace(c(-2, -0.5, 0.5, 3), 0.5, 1.5)", "plaplace([-2, -0.5, 0.5, 3], 0.5, 1.5)", False),
    ("qlaplace", "qlaplace(c(0.1, 0.3, 0.5, 0.8), 0.5, 1.5)", "qlaplace([0.1, 0.3, 0.5, 0.8], 0.5, 1.5)", False),
    ("rlaplace", "rlaplace(4, 0.5, 1.5)", "rlaplace(4, 0.5, 1.5)", True),
    ("dpareto", "dpareto(c(1, 2, 3, 5), 2, 1)", "dpareto([1, 2, 3, 5], 2, 1)", False),
    ("ppareto", "ppareto(c(1, 2, 3, 5), 2, 1)", "ppareto([1, 2, 3, 5], 2, 1)", False),
    ("qpareto", "qpareto(c(0.1, 0.3, 0.5, 0.8), 2, 1)", "qpareto([0.1, 0.3, 0.5, 0.8], 2, 1)", False),
    ("rpareto", "rpareto(4, 2, 1)", "rpareto(4, 2, 1)", True),
    ("drayleigh", "drayleigh(c(0.5, 1, 2, 3), 2)", "drayleigh([0.5, 1, 2, 3], 2)", False),
    ("prayleigh", "prayleigh(c(0.5, 1, 2, 3), 2)", "prayleigh([0.5, 1, 2, 3], 2)", False),
    ("qrayleigh", "qrayleigh(c(0.1, 0.3, 0.5, 0.8), 2)", "qrayleigh([0.1, 0.3, 0.5, 0.8], 2)", False),
    ("rrayleigh", "rrayleigh(4, 2)", "rrayleigh(4, 2)", True),
    ("dlomax", "dlomax(c(0.2, 1, 2, 5), 1.5, 2.5)", "dlomax([0.2, 1, 2, 5], 1.5, 2.5)", False),
    ("plomax", "plomax(c(0.2, 1, 2, 5), 1.5, 2.5)", "plomax([0.2, 1, 2, 5], 1.5, 2.5)", False),
    ("qlomax", "qlomax(c(0.1, 0.3, 0.5, 0.8), 1.5, 2.5)", "qlomax([0.1, 0.3, 0.5, 0.8], 1.5, 2.5)", False),
    ("rlomax", "rlomax(4, 1.5, 2.5)", "rlomax(4, 1.5, 2.5)", True),
    ("dkumar", "dkumar(c(0.1, 0.3, 0.5, 0.8), 2, 3)", "dkumar([0.1, 0.3, 0.5, 0.8], 2, 3)", False),
    ("pkumar", "pkumar(c(0.1, 0.3, 0.5, 0.8), 2, 3)", "pkumar([0.1, 0.3, 0.5, 0.8], 2, 3)", False),
    ("qkumar", "qkumar(c(0.1, 0.3, 0.5, 0.8), 2, 3)", "qkumar([0.1, 0.3, 0.5, 0.8], 2, 3)", False),
    ("rkumar", "rkumar(4, 2, 3)", "rkumar(4, 2, 3)", True),
    ("dfrechet", "dfrechet(c(0.5, 1, 2, 4), 1.5, 0, 1)", "dfrechet([0.5, 1, 2, 4], 1.5, 0, 1)", False),
    ("pfrechet", "pfrechet(c(0.5, 1, 2, 4), 1.5, 0, 1)", "pfrechet([0.5, 1, 2, 4], 1.5, 0, 1)", False),
    ("qfrechet", "qfrechet(c(0.1, 0.3, 0.5, 0.8), 1.5, 0, 1)", "qfrechet([0.1, 0.3, 0.5, 0.8], 1.5, 0, 1)", False),
    ("rfrechet", "rfrechet(4, 1.5, 0, 1)", "rfrechet(4, 1.5, 0, 1)", True),
    ("dgumbel", "dgumbel(c(-1, 0, 1, 2), 0.5, 1.5)", "dgumbel([-1, 0, 1, 2], 0.5, 1.5)", False),
    ("pgumbel", "pgumbel(c(-1, 0, 1, 2), 0.5, 1.5)", "pgumbel([-1, 0, 1, 2], 0.5, 1.5)", False),
    ("qgumbel", "qgumbel(c(0.1, 0.3, 0.5, 0.8), 0.5, 1.5)", "qgumbel([0.1, 0.3, 0.5, 0.8], 0.5, 1.5)", False),
    ("rgumbel", "rgumbel(4, 0.5, 1.5)", "rgumbel(4, 0.5, 1.5)", True),
    ("dgompertz", "dgompertz(c(0, 0.5, 1, 2), 1.2, 0.4)", "dgompertz([0, 0.5, 1, 2], 1.2, 0.4)", False),
    ("pgompertz", "pgompertz(c(0, 0.5, 1, 2), 1.2, 0.4)", "pgompertz([0, 0.5, 1, 2], 1.2, 0.4)", False),
    ("qgompertz", "qgompertz(c(0.1, 0.3, 0.5, 0.8), 1.2, 0.4)", "qgompertz([0.1, 0.3, 0.5, 0.8], 1.2, 0.4)", False),
    ("rgompertz", "rgompertz(4, 1.2, 0.4)", "rgompertz(4, 1.2, 0.4)", True),
    ("dpower", "dpower(c(0.5, 1, 1.5, 2.5), 3, 2)", "dpower([0.5, 1, 1.5, 2.5], 3, 2)", False),
    ("ppower", "ppower(c(0.5, 1, 1.5, 2.5), 3, 2)", "ppower([0.5, 1, 1.5, 2.5], 3, 2)", False),
    ("qpower", "qpower(c(0.1, 0.3, 0.5, 0.8), 3, 2)", "qpower([0.1, 0.3, 0.5, 0.8], 3, 2)", False),
    ("rpower", "rpower(4, 3, 2)", "rpower(4, 3, 2)", True),
    ("dgpd", "dgpd(c(0.5, 1, 2, 4), 0, 1, 0.25)", "dgpd([0.5, 1, 2, 4], 0, 1, 0.25)", False),
    ("pgpd", "pgpd(c(0.5, 1, 2, 4), 0, 1, 0.25)", "pgpd([0.5, 1, 2, 4], 0, 1, 0.25)", False),
    ("qgpd", "qgpd(c(0.1, 0.3, 0.5, 0.8), 0, 1, 0.25)", "qgpd([0.1, 0.3, 0.5, 0.8], 0, 1, 0.25)", False),
    ("rgpd", "rgpd(4, 0, 1, 0.25)", "rgpd(4, 0, 1, 0.25)", True),
    ("dgev", "dgev(c(-1, 0, 1, 2), 0, 1, -0.2)", "dgev([-1, 0, 1, 2], 0, 1, -0.2)", False),
    ("pgev", "pgev(c(-1, 0, 1, 2), 0, 1, -0.2)", "pgev([-1, 0, 1, 2], 0, 1, -0.2)", False),
    ("qgev", "qgev(c(0.1, 0.3, 0.5, 0.8), 0, 1, -0.2)", "qgev([0.1, 0.3, 0.5, 0.8], 0, 1, -0.2)", False),
    ("rgev", "rgev(4, 0, 1, -0.2)", "rgev(4, 0, 1, -0.2)", True),
    ("dtriang", "dtriang(c(0.5, 1, 2, 3.5), 0, 4, 1)", "dtriang([0.5, 1, 2, 3.5], 0, 4, 1)", False),
    ("ptriang", "ptriang(c(0.5, 1, 2, 3.5), 0, 4, 1)", "ptriang([0.5, 1, 2, 3.5], 0, 4, 1)", False),
    ("qtriang", "qtriang(c(0.1, 0.3, 0.5, 0.8), 0, 4, 1)", "qtriang([0.1, 0.3, 0.5, 0.8], 0, 4, 1)", False),
    ("rtriang", "rtriang(4, 0, 4, 1)", "rtriang(4, 0, 4, 1)", True),
]


def _parse(line):
    values = []
    for part in line.strip().split(","):
        text = part.strip()
        if text in ("Inf", "inf", "+Inf"):
            values.append(math.inf)
        elif text in ("-Inf", "-inf"):
            values.append(-math.inf)
        elif text in ("NaN", "nan", "NA"):
            values.append(math.nan)
        else:
            values.append(float(text))
    return np.asarray(values, dtype=float)


def _r_lines():
    body = [
        "suppressPackageStartupMessages(library(extraDistr))",
        "fmt <- function(x) paste(sprintf('%.17g', as.numeric(x)), collapse=',')",
    ]
    for _name, expr, _py, random in CASES:
        if random:
            body.append("set.seed(1)")
        body.append(f"cat(fmt({expr}), '\\n', sep='')")
    script = "\n".join(body)
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != len(CASES):
        raise RuntimeError(result.stderr or result.stdout)
    return lines


def _python(expr, random):
    if random:
        set_seed(1)
    value = eval(expr, {"__builtins__": {}}, closed.__dict__)
    return np.asarray(value, dtype=float).reshape(-1)


def test_closed_matches_r():
    lines = _r_lines()
    failures = []
    for (name, _expr, py, random), line in zip(CASES, lines):
        got = _python(py, random)
        expected = _parse(line)
        if got.shape != expected.shape or not np.allclose(
            got, expected, rtol=1e-8, atol=1e-8, equal_nan=True
        ):
            failures.append(f"{name}\n  py {got}\n  R  {expected}")
    assert not failures, "\n".join(failures)
