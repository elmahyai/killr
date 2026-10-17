import statistics
import time
import sys
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
import numpy as np
from mclust.mclustda_fit import MclustDA, cv_MclustDA
x = np.array([1, 1.1, 1.2, 2, 2.1, 2.2, 4, 4.1, 4.2])
y = ["a", "a", "a", "b", "b", "b", "c", "c", "c"]
fit = MclustDA(x, y, model_type="EDDA", model_names="E", verbose=False)
def one():
    z = cv_MclustDA(fit, nfold=3, verbose=False)
    return np.array([z["ce"], z["brier"]])
value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
