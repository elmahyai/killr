import json
import statistics
import time
import io
import contextlib
from evaluate import evaluate, replay

def one():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        replay(evaluate("1 +\n 2", envir={}))
    return buf.getvalue().rstrip("\n")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
