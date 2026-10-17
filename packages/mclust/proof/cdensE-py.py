import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")

from cdens_fixtures import emit, pars_E, pars_E_missing, pars_E_vanish, print_values, x1
from mclust.cdens_e import cdensE


def one():
    return [
        cdensE(x1, pars_E, logarithm=True),
        cdensE(x1, pars_E, logarithm=False),
        cdensE(x1, pars_E_missing, logarithm=True),
        cdensE(x1, pars_E_vanish, logarithm=True),
    ]


value = one()
print_values([v for res in value for v in emit(res)])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
