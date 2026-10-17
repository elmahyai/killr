import json
import statistics
import time
import os
from evaluate import local_reproducible_output
from evaluate.state import option

def one():
    with local_reproducible_output(width=40, color=False):
        return [int(option("width")), int(os.environ["NO_COLOR"])]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
