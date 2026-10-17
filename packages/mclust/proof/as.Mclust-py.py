import statistics, time, sys
import numpy as np
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.as_mclust import as_mclust
x = {"data": np.array([[-2.],[-1.],[1.],[2.]]), "modelName":"EII",
     "parameters":{"pro":np.array([.4,.6]),"mean":np.array([[-1.,1.]]),
                   "variance":{"modelName":"EII","d":1,"G":2,"scale":1.}}, "G":2,
     "_class":["Mclust"]}
one = lambda: as_mclust(x)["G"]
value = one(); elapsed=[]
for _ in range(20):
    t0=time.perf_counter(); one(); elapsed.append((time.perf_counter()-t0)*1000)
print("%.17g" % value); print("%.17g" % statistics.median(elapsed))
