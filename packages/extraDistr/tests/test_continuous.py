"""Compare continuous extraDistr families with the installed R package."""

import math
import subprocess
import tempfile
import warnings

import numpy as np
import pytest
from boot.rng import set_seed

from extradistr.continuous import (
    dbetapr,
    dbhatt,
    dfatigue,
    dhcauchy,
    dhnorm,
    dht,
    dhuber,
    dinvchisq,
    dinvgamma,
    dlst,
    dnsbeta,
    dprop,
    dsgomp,
    dslash,
    dtnorm,
    dwald,
    pbetapr,
    pbhatt,
    pfatigue,
    phcauchy,
    phnorm,
    pht,
    phuber,
    pinvchisq,
    pinvgamma,
    plst,
    pnsbeta,
    pprop,
    psgomp,
    pslash,
    ptnorm,
    pwald,
    qbetapr,
    qfatigue,
    qhcauchy,
    qhnorm,
    qht,
    qhuber,
    qinvchisq,
    qinvgamma,
    qlst,
    qnsbeta,
    qprop,
    qtlambda,
    qtnorm,
    rbetapr,
    rbhatt,
    rfatigue,
    rhcauchy,
    rhnorm,
    rht,
    rhuber,
    rinvchisq,
    rinvgamma,
    rlst,
    rnsbeta,
    rprop,
    rsgomp,
    rslash,
    rtlambda,
    rtnorm,
    rwald,
)

TOL = 1e-8

# (name, R expression, zero-arg Python callable)
CASES = [
    ("dwald", "dwald(c(0.5,1,2,5,10), 5, 16)", lambda: dwald([0.5, 1, 2, 5, 10], 5, 16)),
    ("dwald", "dwald(c(0.5,1,2,5,10), 5, 16, log=TRUE)", lambda: dwald([0.5, 1, 2, 5, 10], 5, 16, log=True)),
    ("dwald", "dwald(c(1,2), -1, 16)", lambda: dwald([1, 2], -1, 16)),
    ("dwald", "dwald(c(-1,0), 5, 16)", lambda: dwald([-1, 0], 5, 16)),
    ("dwald", "dwald(c(1,5,20), 1, 50)", lambda: dwald([1, 5, 20], 1, 50)),
    ("pwald", "pwald(c(0.5,1,2,5,10), 5, 16)", lambda: pwald([0.5, 1, 2, 5, 10], 5, 16)),
    ("pwald", "pwald(c(1,5,10), 5, 16, lower.tail=FALSE)", lambda: pwald([1, 5, 10], 5, 16, lower_tail=False)),
    ("pwald", "pwald(c(1,5,10), 5, 16, log.p=TRUE)", lambda: pwald([1, 5, 10], 5, 16, log_p=True)),
    ("pwald", "pwald(c(1,5,20), 1, 50)", lambda: pwald([1, 5, 20], 1, 50)),
    ("rwald", "{set.seed(1); rwald(4, 5, 16)}", lambda: (set_seed(1), rwald(4, 5, 16))[1]),
    ("dfatigue", "dfatigue(c(5.1,6,8,12), .5, 2, 5)", lambda: dfatigue([5.1, 6, 8, 12], 0.5, 2, 5)),
    ("dfatigue", "dfatigue(c(5.1,6,8,12), .5, 2, 5, log=TRUE)", lambda: dfatigue([5.1, 6, 8, 12], 0.5, 2, 5, log=True)),
    ("dfatigue", "dfatigue(c(4,5), .5, 2, 5)", lambda: dfatigue([4, 5], 0.5, 2, 5)),
    ("pfatigue", "pfatigue(c(5.1,6,8,12), .5, 2, 5)", lambda: pfatigue([5.1, 6, 8, 12], 0.5, 2, 5)),
    ("qfatigue", "qfatigue(c(0.1,0.5,0.9), .5, 2, 5)", lambda: qfatigue([0.1, 0.5, 0.9], 0.5, 2, 5)),
    ("qfatigue", "qfatigue(c(0,1), .5, 2, 5)", lambda: qfatigue([0, 1], 0.5, 2, 5)),
    ("rfatigue", "{set.seed(1); rfatigue(4, .5, 2, 5)}", lambda: (set_seed(1), rfatigue(4, 0.5, 2, 5))[1]),
    ("dhuber", "dhuber(c(-2,-0.5,0,1,3), 5, 2, 3)", lambda: dhuber([-2, -0.5, 0, 1, 3], 5, 2, 3)),
    ("dhuber", "dhuber(c(-2,0,3), 5, 2, 3, log=TRUE)", lambda: dhuber([-2, 0, 3], 5, 2, 3, log=True)),
    ("phuber", "phuber(c(-2,-0.5,0,1,3), 5, 2, 3)", lambda: phuber([-2, -0.5, 0, 1, 3], 5, 2, 3)),
    ("phuber", "phuber(c(-1,0,2), 0, 1, 1.345, log.p=TRUE, lower.tail=FALSE)", lambda: phuber([-1, 0, 2], 0, 1, 1.345, log_p=True, lower_tail=False)),
    ("qhuber", "qhuber(c(0.1,0.5,0.9), 5, 2, 3)", lambda: qhuber([0.1, 0.5, 0.9], 5, 2, 3)),
    ("qhuber", "qhuber(c(0,0.5,1), 5, 2, 3)", lambda: qhuber([0, 0.5, 1], 5, 2, 3)),
    ("rhuber", "{set.seed(1); rhuber(4, 5, 2, 3)}", lambda: (set_seed(1), rhuber(4, 5, 2, 3))[1]),
    ("dslash", "dslash(c(-2,-0.5,0,1,3), 5, 3)", lambda: dslash([-2, -0.5, 0, 1, 3], 5, 3)),
    ("dslash", "dslash(5, 5, 3)", lambda: dslash(5, 5, 3)),
    ("dslash", "dslash(c(-1,0,2), 0, 2, log=TRUE)", lambda: dslash([-1, 0, 2], 0, 2, log=True)),
    ("pslash", "pslash(c(-2,-0.5,0,1,3), 5, 3)", lambda: pslash([-2, -0.5, 0, 1, 3], 5, 3)),
    ("rslash", "{set.seed(1); rslash(4, 5, 3)}", lambda: (set_seed(1), rslash(4, 5, 3))[1]),
    ("qtlambda", "qtlambda(c(0.1,0.25,0.5,0.8), 0)", lambda: qtlambda([0.1, 0.25, 0.5, 0.8], 0)),
    ("qtlambda", "qtlambda(c(0.1,0.25,0.5,0.8), -1)", lambda: qtlambda([0.1, 0.25, 0.5, 0.8], -1)),
    ("qtlambda", "qtlambda(c(0.1,0.25,0.5,0.8), 2)", lambda: qtlambda([0.1, 0.25, 0.5, 0.8], 2)),
    ("qtlambda", "qtlambda(c(0,0.5,1), 0)", lambda: qtlambda([0, 0.5, 1], 0)),
    ("qtlambda", "qtlambda(c(0,0.5,1), -1)", lambda: qtlambda([0, 0.5, 1], -1)),
    ("qtlambda", "qtlambda(c(0.2,0.7), 0.14, lower.tail=FALSE)", lambda: qtlambda([0.2, 0.7], 0.14, lower_tail=False)),
    ("rtlambda", "{set.seed(1); rtlambda(4, 0.14)}", lambda: (set_seed(1), rtlambda(4, 0.14))[1]),
    ("rtlambda", "{set.seed(1); rtlambda(4, 0)}", lambda: (set_seed(1), rtlambda(4, 0))[1]),
    ("rtlambda", "{set.seed(1); rtlambda(4, -1)}", lambda: (set_seed(1), rtlambda(4, -1))[1]),
    ("dhnorm", "dhnorm(c(0,0.5,1,2,4), 2)", lambda: dhnorm([0, 0.5, 1, 2, 4], 2)),
    ("dhnorm", "dhnorm(c(-1,0), 2)", lambda: dhnorm([-1, 0], 2)),
    ("phnorm", "phnorm(c(0,0.5,1,2,4), 2)", lambda: phnorm([0, 0.5, 1, 2, 4], 2)),
    ("qhnorm", "qhnorm(c(0.1,0.5,0.9), 2)", lambda: qhnorm([0.1, 0.5, 0.9], 2)),
    ("rhnorm", "{set.seed(1); rhnorm(4, 2)}", lambda: (set_seed(1), rhnorm(4, 2))[1]),
    ("dhcauchy", "dhcauchy(c(0,0.5,1,2,4), 2)", lambda: dhcauchy([0, 0.5, 1, 2, 4], 2)),
    ("dhcauchy", "dhcauchy(0, 2, log=TRUE)", lambda: dhcauchy(0, 2, log=True)),
    ("phcauchy", "phcauchy(c(0,0.5,1,2,4), 2)", lambda: phcauchy([0, 0.5, 1, 2, 4], 2)),
    ("qhcauchy", "qhcauchy(c(0.1,0.5,0.9), 2)", lambda: qhcauchy([0.1, 0.5, 0.9], 2)),
    ("rhcauchy", "{set.seed(1); rhcauchy(4, 2)}", lambda: (set_seed(1), rhcauchy(4, 2))[1]),
    ("dht", "dht(c(0,0.5,1,2,4), 2, 2)", lambda: dht([0, 0.5, 1, 2, 4], 2, 2)),
    ("dht", "dht(c(0,1,2), Inf, 1)", lambda: dht([0, 1, 2], math.inf, 1)),
    ("pht", "pht(c(0,0.5,1,2,4), 2, 2)", lambda: pht([0, 0.5, 1, 2, 4], 2, 2)),
    ("qht", "qht(c(0.1,0.5,0.9), 2, 2)", lambda: qht([0.1, 0.5, 0.9], 2, 2)),
    ("qht", "qht(log(c(0.2,0.7)), 3, 2, log.p=TRUE, lower.tail=FALSE)", lambda: qht(np.log([0.2, 0.7]), 3, 2, log_p=True, lower_tail=False)),
    ("rht", "{set.seed(1); rht(4, 2, 2)}", lambda: (set_seed(1), rht(4, 2, 2))[1]),
    ("dlst", "dlst(c(-2,-0.5,0,1,3), 5, 1, 2)", lambda: dlst([-2, -0.5, 0, 1, 3], 5, 1, 2)),
    ("dlst", "dlst(c(-1,0,2), 4, 1, 2, log=TRUE)", lambda: dlst([-1, 0, 2], 4, 1, 2, log=True)),
    ("dlst", "dlst(c(-1,0,1), Inf, 2, 3)", lambda: dlst([-1, 0, 1], math.inf, 2, 3)),
    ("plst", "plst(c(-2,-0.5,0,1,3), 5, 1, 2)", lambda: plst([-2, -0.5, 0, 1, 3], 5, 1, 2)),
    ("plst", "plst(c(-1,0,1), Inf, 2, 3)", lambda: plst([-1, 0, 1], math.inf, 2, 3)),
    ("qlst", "qlst(c(0.1,0.5,0.9), 5, 1, 2)", lambda: qlst([0.1, 0.5, 0.9], 5, 1, 2)),
    ("rlst", "{set.seed(1); rlst(4, 5, 1, 2)}", lambda: (set_seed(1), rlst(4, 5, 1, 2))[1]),
    ("dinvgamma", "dinvgamma(c(0.2,0.5,1,2), 20, 3)", lambda: dinvgamma([0.2, 0.5, 1, 2], 20, 3)),
    ("dinvgamma", "dinvgamma(c(0.2,0.5,1,2), 20, 3, log=TRUE)", lambda: dinvgamma([0.2, 0.5, 1, 2], 20, 3, log=True)),
    ("pinvgamma", "pinvgamma(c(0.2,0.5,1,2), 20, 3)", lambda: pinvgamma([0.2, 0.5, 1, 2], 20, 3)),
    ("pinvgamma", "pinvgamma(c(0.5,2), 4, 2, lower.tail=FALSE, log.p=TRUE)", lambda: pinvgamma([0.5, 2], 4, 2, lower_tail=False, log_p=True)),
    ("qinvgamma", "qinvgamma(c(0.1,0.5,0.9), 20, 3)", lambda: qinvgamma([0.1, 0.5, 0.9], 20, 3)),
    ("qinvgamma", "qinvgamma(c(0.2,0.8), 4, 2, lower.tail=FALSE)", lambda: qinvgamma([0.2, 0.8], 4, 2, lower_tail=False)),
    ("qinvgamma", "qinvgamma(log(c(0.2,0.8)), 4, 2, log.p=TRUE)", lambda: qinvgamma(np.log([0.2, 0.8]), 4, 2, log_p=True)),
    ("rinvgamma", "{set.seed(1); rinvgamma(4, 20, 3)}", lambda: (set_seed(1), rinvgamma(4, 20, 3))[1]),
    ("dinvchisq", "dinvchisq(c(0.05,0.1,0.2,0.5), 20)", lambda: dinvchisq([0.05, 0.1, 0.2, 0.5], 20)),
    ("pinvchisq", "pinvchisq(c(0.05,0.1,0.2,0.5), 20)", lambda: pinvchisq([0.05, 0.1, 0.2, 0.5], 20)),
    ("qinvchisq", "qinvchisq(c(0.1,0.5,0.9), 20)", lambda: qinvchisq([0.1, 0.5, 0.9], 20)),
    ("qinvchisq", "qinvchisq(c(0.2,0.8), 10, lower.tail=FALSE)", lambda: qinvchisq([0.2, 0.8], 10, lower_tail=False)),
    ("rinvchisq", "{set.seed(1); rinvchisq(4, 20)}", lambda: (set_seed(1), rinvchisq(4, 20))[1]),
    ("dinvchisq", "dinvchisq(c(1,2,5,10), 10, 5)", lambda: dinvchisq([1, 2, 5, 10], 10, 5)),
    ("pinvchisq", "pinvchisq(c(1,2,5,10), 10, 5)", lambda: pinvchisq([1, 2, 5, 10], 10, 5)),
    ("qinvchisq", "qinvchisq(c(0.1,0.5,0.9), 10, 5)", lambda: qinvchisq([0.1, 0.5, 0.9], 10, 5)),
    ("qinvchisq", "qinvchisq(log(c(0.2,0.8)), 10, 5, log.p=TRUE)", lambda: qinvchisq(np.log([0.2, 0.8]), 10, 5, log_p=True)),
    ("rinvchisq", "{set.seed(1); rinvchisq(4, 10, 5)}", lambda: (set_seed(1), rinvchisq(4, 10, 5))[1]),
    ("dbetapr", "dbetapr(c(0.2,0.5,1,3,8), 5, 3, 2)", lambda: dbetapr([0.2, 0.5, 1, 3, 8], 5, 3, 2)),
    ("dbetapr", "dbetapr(c(0.5,2), 5, 3, 2, log=TRUE)", lambda: dbetapr([0.5, 2], 5, 3, 2, log=True)),
    ("pbetapr", "pbetapr(c(0.2,0.5,1,3,8), 5, 3, 2)", lambda: pbetapr([0.2, 0.5, 1, 3, 8], 5, 3, 2)),
    ("qbetapr", "qbetapr(c(0.1,0.5,0.9), 5, 3, 2)", lambda: qbetapr([0.1, 0.5, 0.9], 5, 3, 2)),
    ("rbetapr", "{set.seed(1); rbetapr(4, 5, 3, 2)}", lambda: (set_seed(1), rbetapr(4, 5, 3, 2))[1]),
    ("dnsbeta", "dnsbeta(c(-3,-1,0,2,6), 5, 13, -4, 8)", lambda: dnsbeta([-3, -1, 0, 2, 6], 5, 13, -4, 8)),
    ("dnsbeta", "dnsbeta(c(-5,8,9), 2, 3, -4, 8)", lambda: dnsbeta([-5, 8, 9], 2, 3, -4, 8)),
    ("dnsbeta", "dnsbeta(c(-2,0,4), 5, 13, -4, 8, log=TRUE)", lambda: dnsbeta([-2, 0, 4], 5, 13, -4, 8, log=True)),
    ("pnsbeta", "pnsbeta(c(-3,-1,0,2,6), 5, 13, -4, 8)", lambda: pnsbeta([-3, -1, 0, 2, 6], 5, 13, -4, 8)),
    ("qnsbeta", "qnsbeta(c(0.1,0.5,0.9), 5, 13, -4, 8)", lambda: qnsbeta([0.1, 0.5, 0.9], 5, 13, -4, 8)),
    ("rnsbeta", "{set.seed(1); rnsbeta(4, 5, 13, -4, 8)}", lambda: (set_seed(1), rnsbeta(4, 5, 13, -4, 8))[1]),
    ("dprop", "dprop(c(0.1,0.2,0.33,0.5,0.8), 100, 0.33)", lambda: dprop([0.1, 0.2, 0.33, 0.5, 0.8], 100, 0.33)),
    ("dprop", "dprop(c(0.2,0.5), 100, 0.33, prior=1)", lambda: dprop([0.2, 0.5], 100, 0.33, prior=1)),
    ("dprop", "dprop(c(-0.1,0,1,1.2), 10, 0.4)", lambda: dprop([-0.1, 0, 1, 1.2], 10, 0.4)),
    ("dprop", "dprop(c(0.2,0.5), 20, 0.4, log=TRUE)", lambda: dprop([0.2, 0.5], 20, 0.4, log=True)),
    ("pprop", "pprop(c(0.1,0.2,0.33,0.5,0.8), 100, 0.33)", lambda: pprop([0.1, 0.2, 0.33, 0.5, 0.8], 100, 0.33)),
    ("qprop", "qprop(c(0.1,0.5,0.9), 100, 0.33)", lambda: qprop([0.1, 0.5, 0.9], 100, 0.33)),
    ("rprop", "{set.seed(1); rprop(4, 100, 0.33)}", lambda: (set_seed(1), rprop(4, 100, 0.33))[1]),
    ("dbhatt", "dbhatt(c(-2,0,2,5,8), 5, 3, 5)", lambda: dbhatt([-2, 0, 2, 5, 8], 5, 3, 5)),
    ("dbhatt", "dbhatt(c(0,1), 0, 2)", lambda: dbhatt([0, 1], 0, 2)),
    ("dbhatt", "dbhatt(c(1,3,5), 3, 0, 2)", lambda: dbhatt([1, 3, 5], 3, 0, 2)),
    ("dbhatt", "dbhatt(c(1,3,5), 3, 2, 0)", lambda: dbhatt([1, 3, 5], 3, 2, 0)),
    ("dbhatt", "dbhatt(c(0,5,10), 5, 3, 5, log=TRUE)", lambda: dbhatt([0, 5, 10], 5, 3, 5, log=True)),
    ("pbhatt", "pbhatt(c(-2,0,2,5,8), 5, 3, 5)", lambda: pbhatt([-2, 0, 2, 5, 8], 5, 3, 5)),
    ("pbhatt", "pbhatt(c(1,3,5), 3, 0, 2)", lambda: pbhatt([1, 3, 5], 3, 0, 2)),
    ("rbhatt", "{set.seed(1); rbhatt(4, 5, 3, 5)}", lambda: (set_seed(1), rbhatt(4, 5, 3, 5))[1]),
    ("rbhatt", "{set.seed(1); rbhatt(4, 3, 0, 2)}", lambda: (set_seed(1), rbhatt(4, 3, 0, 2))[1]),
    ("rbhatt", "{set.seed(1); rbhatt(4, 3, 2, 0)}", lambda: (set_seed(1), rbhatt(4, 3, 2, 0))[1]),
    ("dtnorm", "dtnorm(c(-1,0,1,2,4), 5, 3, b=7)", lambda: dtnorm([-1, 0, 1, 2, 4], 5, 3, b=7)),
    ("dtnorm", "dtnorm(c(-1,0,1))", lambda: dtnorm([-1, 0, 1])),
    ("dtnorm", "dtnorm(c(-1,7,8), 5, 3, b=7)", lambda: dtnorm([-1, 7, 8], 5, 3, b=7)),
    ("dtnorm", "dtnorm(c(1,4,6), 5, 3, b=7, log=TRUE)", lambda: dtnorm([1, 4, 6], 5, 3, b=7, log=True)),
    ("ptnorm", "ptnorm(c(-1,0,1,2,4), 5, 3, b=7)", lambda: ptnorm([-1, 0, 1, 2, 4], 5, 3, b=7)),
    ("ptnorm", "ptnorm(c(0,0.5,1), a=0, b=1)", lambda: ptnorm([0, 0.5, 1], a=0, b=1)),
    ("qtnorm", "qtnorm(c(0.1,0.5,0.9), 5, 3, b=7)", lambda: qtnorm([0.1, 0.5, 0.9], 5, 3, b=7)),
    ("qtnorm", "qtnorm(c(0,0.5,1), a=0, b=1)", lambda: qtnorm([0, 0.5, 1], a=0, b=1)),
    ("rtnorm", "{set.seed(1); rtnorm(4, 5, 3, b=7)}", lambda: (set_seed(1), rtnorm(4, 5, 3, b=7))[1]),
    ("rtnorm", "{set.seed(1); rtnorm(4, a=0)}", lambda: (set_seed(1), rtnorm(4, a=0))[1]),
    ("rtnorm", "{set.seed(1); rtnorm(4, b=0)}", lambda: (set_seed(1), rtnorm(4, b=0))[1]),
    ("rtnorm", "{set.seed(1); rtnorm(4, a=0, b=1)}", lambda: (set_seed(1), rtnorm(4, a=0, b=1))[1]),
    ("rtnorm", "{set.seed(1); rtnorm(4, mean=-6, a=0)}", lambda: (set_seed(1), rtnorm(4, mean=-6, a=0))[1]),
    ("rtnorm", "{set.seed(1); rtnorm(4, mean=8, b=0)}", lambda: (set_seed(1), rtnorm(4, mean=8, b=0))[1]),
    ("rtnorm", "{set.seed(1); rtnorm(4, a=3, b=5)}", lambda: (set_seed(1), rtnorm(4, a=3, b=5))[1]),
    ("dsgomp", "dsgomp(c(0,0.5,1,3,8), 0.4, 1)", lambda: dsgomp([0, 0.5, 1, 3, 8], 0.4, 1)),
    ("dsgomp", "dsgomp(c(0.5,1,3), 0.4, 1, log=TRUE)", lambda: dsgomp([0.5, 1, 3], 0.4, 1, log=True)),
    ("psgomp", "psgomp(c(0,0.5,1,3,8), 0.4, 1)", lambda: psgomp([0, 0.5, 1, 3, 8], 0.4, 1)),
    ("psgomp", "psgomp(c(1,3), 0.4, 1, lower.tail=FALSE, log.p=TRUE)", lambda: psgomp([1, 3], 0.4, 1, lower_tail=False, log_p=True)),
    ("rsgomp", "{set.seed(1); rsgomp(4, 0.4, 1)}", lambda: (set_seed(1), rsgomp(4, 0.4, 1))[1]),
    ("dwald", "dwald(c(1,2,3), c(5,6), 16)", lambda: dwald([1, 2, 3], [5, 6], 16)),
    ("dwald", "dwald(numeric(), 1, 1)", lambda: dwald([], 1, 1)),
    ("dwald", "dwald(NaN, 5, 16)", lambda: dwald(float("nan"), 5, 16)),
]


def _parse_r(text):
    if text == "":
        return np.array([], dtype=float)
    out = []
    for part in text.split(","):
        if part in ("NA", "NaN"):
            out.append(math.nan)
        elif part == "Inf":
            out.append(math.inf)
        elif part == "-Inf":
            out.append(-math.inf)
        else:
            out.append(float(part))
    return np.asarray(out, dtype=float)


@pytest.fixture(scope="module")
def r_values():
    lines = ["suppressPackageStartupMessages(library(extraDistr))"]
    for i, (_, expr, _) in enumerate(CASES):
        lines.append(f'cat("CASE {i}\\n")')
        lines.append(f"x <- {expr}")
        lines.append('cat(paste(sprintf("%.17g", as.numeric(x)), collapse=","), "\\n", sep="")')
    script = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False) as handle:
        handle.write(script)
        path = handle.name
    completed = subprocess.run(
        ["Rscript", path],
        check=True,
        capture_output=True,
        text=True,
    )
    values = {}
    rows = completed.stdout.splitlines()
    index = 0
    while index < len(rows):
        if rows[index].startswith("CASE "):
            values[int(rows[index].split()[1])] = _parse_r(rows[index + 1])
            index += 2
        else:
            index += 1
    return values


@pytest.mark.parametrize("index", range(len(CASES)))
def test_matches_r(index, r_values):
    name, expr, call = CASES[index]
    got = np.asarray(call(), dtype=float).reshape(-1)
    expected = r_values[index]
    assert got.shape == expected.shape, (name, expr, got, expected)
    assert np.allclose(got, expected, rtol=TOL, atol=TOL, equal_nan=True), (
        name,
        expr,
        got.tolist(),
        expected.tolist(),
    )


def test_bad_parameters_warn_once():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = dwald([1.0, 2.0], [-1.0, -2.0], 16)
    assert np.isnan(result).all()
    assert len(caught) == 1
    assert str(caught[0].message) == "NaNs produced"


def test_nan_input_does_not_warn():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = pwald(float("nan"), 5, 16)
    assert math.isnan(result[0])
    assert caught == []


def test_rng_bad_parameter_warns_once():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = rsgomp(3, -1, 1)
    assert np.isnan(result).all()
    assert len(caught) == 1
    assert str(caught[0].message) == "NAs produced"
