import statistics,sys,time,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.hypvol import hypvol
def one(): return [hypvol(np.array([[1,4],[2,5],[3,7.]])),hypvol(np.arange(1,6),True)]
value=one();elapsed=[]
for _ in range(20):
 t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
for x in value: print("%.17g"%x)
print("%.17g"%statistics.median(elapsed))
