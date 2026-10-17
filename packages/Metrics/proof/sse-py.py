import sys,time,statistics,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/Metrics")
from Metrics.sse import sse
actual=np.array([1.1,1.9,3.,4.4,5.,5.6]); predicted=np.array([.9,1.8,2.5,4.5,5.,6.2])
def f(): return sse(actual,predicted)
f(); times=[]
for _ in range(20):
 t=time.perf_counter(); z=f(); times.append(time.perf_counter()-t)
z=f()
arr=np.asarray(z)
print("result",",".join(format(float(x),".17e") for x in arr.flat))
print("py_ms",format(statistics.median(times)*1000,".17e"))
