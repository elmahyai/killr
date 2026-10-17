import json
import statistics
import sys
import time

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/packages/cluster",
    "/home/ahmed/killr_projects/killr/packages/proxy",
]
from boot.resample import _sample_positions
from boot.rng import set_seed
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "mass_r_rng",
    "/home/ahmed/killr_projects/killr/packages/MASS/mass/_r_rng.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
norm_rand = _mod.norm_rand
from e1071.match_controls import match_controls


def one():
    set_seed(4242)
    age_case = [40 + 5 * norm_rand() for _ in range(50)]
    age_cont = [45 + 10 * norm_rand() for _ in range(150)]
    age = age_case + age_cont
    sex_case = _sample_positions(["M", "F"], 50, replace=True, prob=[0.4, 0.6])
    sex_cont = _sample_positions(["M", "F"], 150, replace=True, prob=[0.6, 0.4])
    sex = sex_case + sex_cont
    casecont = ["case"] * 50 + ["cont"] * 150
    m = match_controls("casecont ~ Sex + Age", {"casecont": casecont, "Sex": sex, "Age": age})
    fac = []
    for value in m["factor"]:
        if value is None or (isinstance(value, float) and value != value):
            fac.append(0)
        else:
            fac.append(1 if value == "case" else 2)
    return [int(name) for name in m["controls"]] + fac


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
