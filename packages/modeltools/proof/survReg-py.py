import statistics
import sys
import time
from pathlib import Path

import numpy as np
from survival.surv import Surv

sys.path.insert(0, str(Path(__file__).parents[2] / "modeltools"))
from modeltools.core import ModelEnv, survReg

n = 80
i = np.arange(1, n + 1)
time_values = 0.4 + ((i * 19) % 31) / 10
status = np.where(i % 4 == 0, 0.0, 1.0)
x = ((i * 7) % 13) / 5 - 1
wt = 1 + (i % 3) / 2
env = ModelEnv(
    values={
        "response": Surv(time_values, status),
        "input": {"x": x},
    }
)


def one():
    fit = survReg.fit(env, weights=wt, dist="extreme")
    return np.ravel(
        np.concatenate(
            [fit["coefficients"], np.ravel(fit["scale"]), np.ravel(fit["loglik"][-1:])]
        )
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(f"{float(v):.17g}" for v in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
