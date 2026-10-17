import json
import statistics
import tempfile
import time

from memoise import (
    cache_filesystem,
    cache_memory,
    drop_cache,
    forget,
    has_cache,
    is_memoised,
    is_memoized,
    memoise,
    memoize,
    timeout,
)

def one():
    n = {"n": 0}

    def f(x):
        n["n"] += 1
        return x + 3

    m = memoize(f)
    return [m(2), m(2), n["n"]]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
