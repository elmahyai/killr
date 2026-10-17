import statistics
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.em_xxi import emXXI
x = np.array([[-1.2,.5,2.1,1.7],[-.3,.9,3.2,1.1],[.4,-.8,1.3,2.6],[2.2,1.5,-1.1,.7],[1.1,-1.7,.2,3.4],[3.3,.2,2.4,-.5]])
def one():
    y = emXXI(x)
    v = y["parameters"]["variance"]
    return np.concatenate([np.ravel(y["parameters"]["mean"], order="F"), [v["scale"]],
                           np.ravel(v["shape"], order="F"), np.ravel(v["Sigma"], order="F"), [y["loglik"]]])
value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
