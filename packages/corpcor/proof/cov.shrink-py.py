
import json, statistics, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
from corpcor import *
X = np.array([
 [1.2, 0.4, -0.2, 0.7],
 [0.3, 1.1, 0.5, -0.4],
 [-0.6, 0.2, 1.4, 0.1],
 [0.8, -0.3, 0.2, 1.5],
 [0.1, 0.9, -0.7, 0.3],
 [-0.4, 0.6, 0.8, -0.2],
], dtype=float)
M = np.array([[2.0, 0.4, 0.1],[0.4, 1.5, -0.2],[0.1, -0.2, 1.2]])
w = np.array([0.1, 0.2, 0.05, 0.25, 0.15, 0.25])
def flat(value):
    return np.asarray(value, dtype=float).reshape(-1, order="F").tolist()

def one():
    return flat(cov_shrink(X, verbose=False))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
