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
    x = [[0, 1], [1, 0], [0.5, 0.5], [1, 1], [0.2, 0.8]]
    y = [[1, 0], [0, 1], [1, 0], [0, 1], [1, 0]]
    fit = nnet(x, y, size=2, softmax=True, decay=0.01, Wts=[0.1] * 12, maxit=20, trace=False)
    return [float(v) for v in fit["wts"]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
