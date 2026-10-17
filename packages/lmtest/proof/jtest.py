from lmtest import jtest
import numpy as np
x = np.array([1,3,2,6,5,8,7,4,9,10,12,11,15,13,14,18,16,19,17,20], float)
y = np.array([2,2,4,3,7,6,9,8,5,11,10,14,12,16,15,13,19,17,20,18], float)
z = np.sqrt(x)

def one():
    j = jtest(y, x, z)
    rows = np.column_stack([j["estimate"], j["std_error"], j["t"], j["p_value"]])
    return ",".join(f"{v:.17g}" for v in rows.reshape(-1))

import statistics
import time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + str(value).replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
