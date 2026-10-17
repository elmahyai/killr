import sys,time,statistics,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/Metrics")
from Metrics.ScoreQuadraticWeightedKappa import ScoreQuadraticWeightedKappa
rater_a=np.array([1,4,5,5,2,1]); rater_b=np.array([2,2,4,5,3,3])
def f(): return ScoreQuadraticWeightedKappa(rater_a,rater_b,1,5)
f(); times=[]
for _ in range(20):
 t=time.perf_counter(); z=f(); times.append(time.perf_counter()-t)
z=f()
arr=np.asarray(z)
print("result",",".join(format(float(x),".17e") for x in arr.flat))
print("py_ms",format(statistics.median(times)*1000,".17e"))
