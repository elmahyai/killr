import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

from cdens_fixtures import X, emit, pars_EEI, pars_EEI_missing, print_values
from mclust.cdens_eei import cdensEEI


def one():
    return [
        cdensEEI(X, pars_EEI, logarithm=True),
        cdensEEI(X, pars_EEI, logarithm=False),
        cdensEEI(X, pars_EEI_missing, logarithm=True),
    ]


value = one()
print_values([v for res in value for v in emit(res)])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
