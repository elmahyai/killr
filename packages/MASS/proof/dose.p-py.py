import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass.dose_p import dose_p


class _Family:
    def __init__(self, linkfun):
        self.linkfun = linkfun


class _GlmFit:
    def __init__(self, coefficients, vcov_matrix, family):
        self.coefficients = np.asarray(coefficients, dtype=float)
        self.vcov_matrix = np.asarray(vcov_matrix, dtype=float)
        self.family = family


def _logit_linkfun(p):
    p = np.asarray(p, dtype=float)
    return np.log(p / (1.0 - p))


def _probit_linkfun(p):
    from mass.boxcox import _pnorm_inv

    flat = np.asarray(p, dtype=float).reshape(-1)
    return np.array([_pnorm_inv(float(x)) for x in flat], dtype=float)


LOGIT_COEF = np.array([-3.4731553070866998, -2.3724119440915521, 1.0642139699192439])
LOGIT_VCOV = np.array(
    [
        [0.219511212333241584, 0.120758436460768628, -0.052507473315858193],
        [0.120758436460768628, 0.148618561292899576, -0.039514121348950042],
        [-0.052507473315858193, -0.039514121348950042, 0.017181297912909156],
    ]
)
PROBIT_COEF = np.array([-2.06032964869793389, -1.40668491670368279, 0.63244859158874445])
PROBIT_VCOV = np.array(
    [
        [0.062935074984636671, 0.033678650502478438, -0.0145012097435807136],
        [0.033678650502478438, 0.045368908101401526, -0.0112983866526863829],
        [-0.014501209743580714, -0.011298386652686383, 0.0048648111539570426],
    ]
)

P = np.array([0.25, 0.5, 0.75], dtype=float)


def one():
    logit = _GlmFit(LOGIT_COEF, LOGIT_VCOV, _Family(_logit_linkfun))
    probit = _GlmFit(PROBIT_COEF, PROBIT_VCOV, _Family(_probit_linkfun))
    d1 = dose_p(logit, cf=(1, 3), p=P)
    d2 = dose_p(probit, cf=(1, 3), p=P)
    return np.concatenate([d1.dose, d1.se, d2.dose, d2.se])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
