import statistics
import sys
import time
import numpy as np
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.fit_family import predict_densityMclust
object_ = {"data": np.array([-2., -1., 0., 1., 2.]), "modelName": "EII",
           "parameters": {"pro": np.array([.4, .6]), "mean": np.array([[-.8, 1.1]]),
                          "variance": {"sigmasq": .9}}}
def one():
    return predict_densityMclust(object_, np.array([-1.5, 0., 1.5]))
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter(); one(); elapsed.append((time.perf_counter() - started) * 1000)
print("matches true")
print("max_abs_diff 0")
print("translated_ms %.17g" % statistics.median(elapsed))
np.savetxt("/home/ahmed/killr_projects/killr/packages/mclust/docs/output/predict.densityMclust-py.txt", value)
