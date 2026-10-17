import statistics, time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
def one():
    from quantreg import rq_fit_fnc
    f = rq_fit_fnc(X, y, np.array([[0.0, 1.0, 0.0]]), [0.0], tau=0.5)
    return np.concatenate([f['coefficients'], f['residuals'], f['it']])
one()
elapsed=[]
for _ in range(20):
 s=time.perf_counter(); one(); elapsed.append((time.perf_counter()-s)*1000)
value=one()
arr=np.atleast_1d(np.asarray(value,dtype=float)).reshape(-1)
print(','.join(f'{v:.17g}' for v in arr))
print(f'{statistics.median(elapsed):.17g}')
