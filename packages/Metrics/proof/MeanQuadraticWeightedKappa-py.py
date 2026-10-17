import sys,time,statistics,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/Metrics")
from Metrics.MeanQuadraticWeightedKappa import MeanQuadraticWeightedKappa
kappas=np.array([.3,.2,.2,.5,.1,.2]); weights=np.array([1,2.5,1,1,2,3])
def f(): return MeanQuadraticWeightedKappa(kappas,weights)
f(); times=[]
for _ in range(20):
 t=time.perf_counter(); z=f(); times.append(time.perf_counter()-t)
z=f()
arr=np.asarray(z)
print("result",",".join(format(float(x),".17e") for x in arr.flat))
print("py_ms",format(statistics.median(times)*1000,".17e"))
