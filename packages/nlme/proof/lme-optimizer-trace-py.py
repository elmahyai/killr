"""Diagnostic: record every objective evaluation that lme() makes inside nlminb.

Mirrors ``lme-optimizer-trace-r.R``. Each ``EVAL`` line is a parameter vector
that PORT (``nlminb_port``) passed to the objective, and ``VAL`` is the
logLik that ``mixed_loglik`` returns for it: the Koshal intercept
(R's ``logLik.lmeStructInt`` with ``gradHess`` on).
"""

import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

import numpy as np  # noqa: E402
import nlme_mixedem  # noqa: E402
import nlme.lme_family as lme_family  # noqa: E402

source = (PACKAGE / "proof" / "lme-py.py").read_text().split("value = one()")[0]
exec(compile(source, "lme-py-head", "exec"))

log = []
original_loglik = nlme_mixedem.mixed_loglik


def traced(xy, pdims, pars, settings, sigma):
    value = original_loglik(xy, pdims, pars, settings, sigma)
    log.append((list(pars), float(np.asarray(value[0], dtype=np.float64)[0])))
    return value


nlme_mixedem.mixed_loglik = traced
original_fit = lme_family._optimize_variance_fit
summary = {}


def fit_traced(start, con, block, control, reml):
    par, info = original_fit(start, con, block, control, reml)
    summary.update(info)
    print("NLMINB start %s" % " ".join("%.17g" % v for v in start))
    return par, info


lme_family._optimize_variance_fit = fit_traced
fit = lme_family.lme("distance ~ age", data=orthodont(), control={"apVar": False})

for index, (point, value) in enumerate(log, 1):
    print("EVAL %d %s" % (index, " ".join("%.17g" % v for v in point)))
    print("VAL %.17g" % value)
print("NEVAL %d" % len(log))
print(
    "NLMINB par %s obj %.17g conv %d iter %d evals %d %d %s"
    % (
        " ".join("%.17g" % v for v in summary["par"]),
        summary["objective"],
        summary["convergence"],
        summary["iterations"],
        summary["evaluations"]["function"],
        summary["evaluations"]["gradient"],
        summary["message"],
    )
)
print("FIT sigma %.17g logLik %.17g" % (fit.sigma, fit.loglik))
print("FIXED %s" % " ".join("%.17g" % v for v in fit.fixed))
print("PARAMS %s" % " ".join("%.17g" % v for v in fit.model_parameters))
print("ANOVA_F %s" % " ".join("%.17g" % v for v in lme_family.numeric_anova(lme_family.anova_lme(fit))[4:6]))
