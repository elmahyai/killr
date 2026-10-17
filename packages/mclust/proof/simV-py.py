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
    pars_V,
    pars_V_nopro,
    pars_V_missing,
    pars_V_zero,
)
from mclust.sim_v import simV


def step(res):
    return emit(res) + tail_draws()


def one():
    out = []
    out += step(simV(pars_V, 60, seed=42))
    out += step(simV(pars_V_nopro, 45, seed=7))
    out += step(simV(pars_V, 300, seed=2024))
    out += step(simV(pars_V_missing, 10, seed=1))
    out += step(simV(pars_V_zero, 30, seed=3))
    return out


value = one()
print_values(value)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
