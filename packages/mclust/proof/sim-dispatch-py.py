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
    pars_E,
    pars_E_nopro,
    pars_V,
    pars_EII,
    pars_EEI,
    pars_EEE,
    pars_EEE_missing,
    pars_EEV,
    pars_EVI,
    pars_VEI,
)
from mclust.sim import sim


def step(res):
    return emit(res) + tail_draws()


def one():
    out = []
    out += step(sim("E", pars_E, 60, seed=42))
    out += step(sim("X", pars_E_nopro, 45, seed=7))
    out += step(sim("V", pars_V, 300, seed=2024))
    out += step(sim("XII", pars_EII, 60, seed=42))
    out += step(sim("XXI", pars_EEI, 45, seed=7))
    out += step(sim("XXX", pars_EEE, 300, seed=2024))
    out += step(sim("EEV", pars_EEV, 60, seed=42))
    out += step(sim("EVI", pars_EVI, 45, seed=7))
    out += step(sim("VEI", pars_VEI, 300, seed=2024))
    out += step(sim("EEE", pars_EEE_missing, 10, seed=1))
    return out


value = one()
print_values(value)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
