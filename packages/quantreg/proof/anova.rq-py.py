import statistics
import time
import numpy as np
A = np.loadtxt("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt")
data = {"y": A[:, 3], "x1": A[:, 1], "x2": A[:, 2]}
from quantreg import rq
fit = rq("y ~ x1 + x2", tau=[0.25, 0.5, 0.75], data=data)
from quantreg import anova_rq
def _once():
    try:
        anova_rq(fit)
    except RuntimeError as error:
        return str(error)

def one():
    return _once()
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
print(value)
print(f'{statistics.median(elapsed):.17g}')
