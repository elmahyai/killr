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
    w = [0.1, -0.2, 0.3, 0.0, 0.4, -0.1, 0.2, 0.5, -0.3]
    data = {"y": [0.2, 0.8, 0.4, 0.9], "x1": [0, 1, 0.5, 1], "x2": [1, 0, 0.5, 1]}
    fit = nnet_formula("y ~ x1 + x2", data, size=2, linout=True, decay=0.01, Wts=w, maxit=30, trace=False)
    return [float(v) for v in fit["wts"]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
