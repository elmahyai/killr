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
    a = tempfile.mktemp(); b = tempfile.mktemp()
    open(a, "wb").write(bytes([1, 2, 3]))
    open(b, "wb").write(bytes([1, 2, 3]))
    return compare_file_binary(a, b)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
