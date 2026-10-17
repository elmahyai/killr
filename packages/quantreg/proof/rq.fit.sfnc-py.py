import statistics
import time
import numpy as np
import scipy.sparse as sp
from quantreg.sfn import rq_fit_sfnc
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
a = sp.csr_matrix(X)
R1 = sp.csr_matrix(np.array([[0.0, 0.0, 1.0]]))
R2 = sp.csr_matrix(np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]))
def one():
    f1 = rq_fit_sfnc(a, y, R1, np.array([0.0]), tau=0.5)
    f2 = rq_fit_sfnc(a, y, R2, np.array([0.0, 3.0]), tau=0.25)
    return np.concatenate([
        f1['coefficients'], f1['residuals'], [f1['it'], f1['ierr']],
        f2['coefficients'], f2['residuals'], [f2['it'], f2['ierr']],
    ])
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
array = np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
