import statistics,sys,time,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.random_pairs import randomPairs
def one():
 p=randomPairs(np.array([[1],[2]]),seed=7);return [*p.shape,p.sum()]
value=one();elapsed=[]
for _ in range(20):
 t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
for x in value: print("%.17g"%x)
print("%.17g"%statistics.median(elapsed))
