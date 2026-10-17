import statistics, sys, time
import numpy as np
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.me_eee_ev_xxx import meEEV
from mclust.em_control import em_control
i=np.arange(1,41); g=(i>20).astype(float)
X=np.column_stack([((i*37)%11)/11+2.5*g,((i*23)%13)/13+1.5*g])
w=((i*7)%19)/19; Z=np.column_stack([.2+.6*w,.8-.6*w])
def flat(a):
    v=a["parameters"]["variance"]
    q=[a["loglik"],a["returnCode"],a["info"]["iterations"],a["info"]["error"]]
    for x in (a["parameters"]["pro"],a["parameters"]["mean"],v["scale"],v["shape"],v["orientation"],v["sigma"],a["z"]):
        q += list(np.asarray(x,dtype=float).ravel(order="F"))
    return q
def one(): return flat(meEEV(X,Z,control=em_control(),warn=False))
value=one(); elapsed=[]
for _ in range(20):
    t0=time.perf_counter(); one(); elapsed.append((time.perf_counter()-t0)*1000)
for x in value: print("%.17g"%x)
print("%.17g"%statistics.median(elapsed))
