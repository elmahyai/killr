import statistics,sys,time,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.covw import covw
def one():
 o=covw(np.arange(1,7).reshape(3,2,order="F"),np.array([[1,2],[2,1],[1,3]]))
 return np.concatenate((o["mean"].ravel(order="F"),o["S"].ravel(order="F"),o["W"].ravel(order="F")))
value=one();elapsed=[]
for _ in range(20):
 t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
for x in value: print("%.17g"%x)
print("%.17g"%statistics.median(elapsed))
