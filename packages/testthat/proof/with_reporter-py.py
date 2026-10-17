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
    with with_reporter(MinimalReporter()) as reporter:
        _ = 7
    return type(reporter).__name__
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
