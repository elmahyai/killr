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
    def f(x):
        return x

    m = memoise(f)
    return [int(is_memoised(f)), int(is_memoised(m))]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
