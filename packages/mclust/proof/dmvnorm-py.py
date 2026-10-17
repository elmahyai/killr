import statistics,sys,time,numpy as np
sys.path.insert(0,"/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.dmvnorm import dmvnorm
def one(): return dmvnorm(np.array([[0.,0.],[1.,-1.]]),mean=[0.,0.],sigma=np.eye(2))
value=one(); elapsed=[]
for _ in range(20):
 t=time.perf_counter();one();elapsed.append((time.perf_counter()-t)*1000)
for x in value: print("%.17g"%x)
print("%.17g"%statistics.median(elapsed))
