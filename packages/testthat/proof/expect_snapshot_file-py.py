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
    with local_edition(3):
        fd, f = tempfile.mkstemp()
        os.close(fd)
        open(f, "w").write("hi\n")
        return expect_snapshot_file(f, "demo")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
