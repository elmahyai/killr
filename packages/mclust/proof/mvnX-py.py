import statistics
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mvn import mvnX
x = np.array([-1.2, 0.5, 2.1, 1.7, -0.3, 0.9, 3.2, 1.1])
def one():
    y = mvnX(x)
    return np.array([y["parameters"]["mean"].flat[0], y["parameters"]["variance"]["sigmasq"], y["loglik"]])
value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
