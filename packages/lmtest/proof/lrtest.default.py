from lmtest import lrtest
import numpy as np
x = np.array([1,3,2,6,5,8,7,4,9,10,12,11,15,13,14,18,16,19,17,20], float)
y = np.array([2,2,4,3,7,6,9,8,5,11,10,14,12,16,15,13,19,17,20,18], float)
z = np.sqrt(x)

def one():
    lr = lrtest(y, x)
    return f"{lr['df_model'][0]:.17g},{lr['df_model'][1]:.17g},{lr['loglik'][0]:.17g},{lr['loglik'][1]:.17g},{lr['df']:.17g},{lr['statistic']:.17g},{lr['p_value']:.17g}"

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
