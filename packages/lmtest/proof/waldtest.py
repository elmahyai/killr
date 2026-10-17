from lmtest import waldtest
import numpy as np
x = np.array([1,3,2,6,5,8,7,4,9,10,12,11,15,13,14,18,16,19,17,20], float)
y = np.array([2,2,4,3,7,6,9,8,5,11,10,14,12,16,15,13,19,17,20,18], float)
z = np.sqrt(x)

def one():
    w = waldtest(y, x)
    return f"{w['res_df'][0]:.17g},{w['res_df'][1]:.17g},{w['df']:.17g},{w['statistic']:.17g},{w['p_value']:.17g}"

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
