import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

from cdens_fixtures import (
    X,
    emit,
    pars_E,
    pars_EEE,
    pars_EEI,
    pars_EEV,
    pars_EII,
    pars_EVI,
    print_values,
    x1,
)
from mclust.cdens import cdens


def one():
    return [
        cdens(x1, "E", pars_E, logarithm=True),
        cdens(x1, "X", pars_E, logarithm=True),
        cdens(X, "EII", pars_EII, logarithm=True),
        cdens(X, "XII", pars_EII, logarithm=False),
        cdens(X, "EEI", pars_EEI, logarithm=True),
        cdens(X, "XXI", pars_EEI, logarithm=False),
        cdens(X, "EVI", pars_EVI, logarithm=True),
        cdens(X, "EEV", pars_EEV, logarithm=True),
        cdens(X, "EEE", pars_EEE, logarithm=True),
        cdens(X, "XXX", pars_EEE, logarithm=False),
    ]


value = one()
print_values([v for res in value for v in emit(res)])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
