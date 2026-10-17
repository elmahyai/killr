import statistics
import sys
import time
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
warnings.simplefilter("ignore")

from sim_core_fixtures import (
    emit,
    print_values,
    tail_draws,
    pars_EVI,
    pars_EVI_nopro,
    pars_EVI_missing,
)
from mclust.sim_evi import simEVI


def step(res):
    return emit(res) + tail_draws()


def one():
    out = []
    out += step(simEVI(pars_EVI, 60, seed=42))
    out += step(simEVI(pars_EVI_nopro, 45, seed=7))
    out += step(simEVI(pars_EVI, 300, seed=2024))
    out += step(simEVI(pars_EVI_missing, 10, seed=1))
    return out


value = one()
print_values(value)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
