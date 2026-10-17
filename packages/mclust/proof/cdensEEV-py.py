import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

from cdens_fixtures import X, emit, pars_EEV, pars_EEV_missing, print_values
from mclust.cdens_eev import cdensEEV


def one():
    return [
        cdensEEV(X, pars_EEV, logarithm=True),
        cdensEEV(X, pars_EEV, logarithm=False),
        cdensEEV(X, pars_EEV_missing, logarithm=True, warn=False),
    ]


value = one()
print_values([v for res in value for v in emit(res)])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
