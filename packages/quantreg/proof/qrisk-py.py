import statistics, time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
def one():
    from quantreg import qrisk
    f = qrisk(X, mu=0.0, lambda_=100)
    return np.concatenate([f['pihat'], [f['muhat'], f['qrisk']]])
one()
elapsed=[]
for _ in range(20):
 s=time.perf_counter(); one(); elapsed.append((time.perf_counter()-s)*1000)
value=one()
arr=np.atleast_1d(np.asarray(value,dtype=float)).reshape(-1)
print(','.join(f'{v:.17g}' for v in arr))
print(f'{statistics.median(elapsed):.17g}')
