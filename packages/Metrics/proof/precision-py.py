import sys,time,statistics,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/Metrics")
from Metrics.precision import precision
actual=np.array([1,1,1,0,0,0]); predicted=np.array([1,0,1,1,1,1])
def f(): return precision(actual,predicted)
f(); times=[]
for _ in range(20):
 t=time.perf_counter(); z=f(); times.append(time.perf_counter()-t)
z=f()
arr=np.asarray(z)
print("result",",".join(format(float(x),".17e") for x in arr.flat))
print("py_ms",format(statistics.median(times)*1000,".17e"))
