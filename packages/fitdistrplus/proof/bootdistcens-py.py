import time, numpy as np
from fitdistrplus import *
x=np.array([1.,2.,3.,4.,5.])
def call():
    return fitdist(x,"norm")
call(); ts=[]
for _ in range(20):
    t=time.perf_counter(); y=call(); ts.append((time.perf_counter()-t)*1000)
print({"value":y.get("estimate",y),"median_ms":float(np.median(ts))})
