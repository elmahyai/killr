import json
import os
import statistics
import tempfile
import time
import warnings
warnings.filterwarnings('ignore')
from testthat import *
def caught(fn):
    try:
        fn()
        return ''
    except Exception as exc:
        return str(exc)
def one():
    import numpy as np
    x = np.arange(1, 5).reshape(2, 2)
    return "x".join(str(int(v)) for v in expect_shape(x, nrow=2).shape)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
