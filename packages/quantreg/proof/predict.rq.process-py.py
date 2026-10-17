import statistics
import time
import numpy as np
from quantreg.process import predict_rq_process, rq_fit_br_process
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
# The process comes from the Rust crate quantreg_br (rqbr.f port), outside the timed call.
fit = rq_fit_br_process(X, y)
# The new rows as a model matrix with intercept; the formula step is not translated.
newdata = np.column_stack([np.ones(6), [-1.5, -0.5, 0.0, 0.5, 1.5, 2.2], [0.3, -1.0, 0.8, 0.0, -0.4, 1.1]])
def one():
    return predict_rq_process(fit, newdata)
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
array = np.asarray(value, dtype=float).ravel(order="F")
print(','.join(f'{item:.17g}' for item in array))
print(f'{statistics.median(elapsed):.17g}')
