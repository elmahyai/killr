import statistics
import time
import numpy as np
from quantreg.process import predict_rq_process, rq_fit_br_process, ranks
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
X = A[:, :3]
y = A[:, 3]
# The process comes from the Rust crate quantreg_br (rqbr.f port), outside the timed call.
fit = rq_fit_br_process(X, y)
def one():
    a = ranks(fit)
    b = ranks(fit, trim=(0.1, 0.9))
    c1 = ranks(fit, score="normal")
    c2 = ranks(fit, score="sign")
    c3 = ranks(fit, score="tau", tau=0.25)
    c4 = ranks(fit, score="normalscale")
    c5 = ranks(fit, score="halfnormalscale")
    c6 = ranks(fit, score="lehmann")
    c7 = ranks(fit, score="interquartile")
    parts = [a, b, c1, c2, c3, c4, c5, c6, c7]
    out = []
    for part in parts:
        out.extend(part["ranks"].tolist())
        out.append(part["A2"])
    return out
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
