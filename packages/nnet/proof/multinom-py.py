import json
import statistics
import sys
import time
import warnings

import numpy as np

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/nnet"]
warnings.filterwarnings("ignore")
from nnet import multinom, nnet, nnet_default, nnet_formula, nnet_hess

def one():
    data = {"y": ["a", "b", "a", "c", "b", "c"], "x": [0.0, 1, 0.2, 0.8, 0.4, 0.9]}
    fit = multinom("y ~ x", data, maxit=40, trace=False)
    return [float(v) for v in fit["wts"]] + [float(fit["deviance"]), float(fit["AIC"])]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
