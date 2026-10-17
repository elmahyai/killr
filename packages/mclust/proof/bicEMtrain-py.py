import statistics
import time
import sys
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.mclustda_fit import bicEMtrain
x = [1, 1.1, 1.2, 2, 2.1, 2.2, 4, 4.1, 4.2]
y = ["a", "a", "a", "b", "b", "b", "c", "c", "c"]
def one():
    z = bicEMtrain(x, y, modelNames=["E", "V"])
    return [z["E"], z["V"]]
value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
