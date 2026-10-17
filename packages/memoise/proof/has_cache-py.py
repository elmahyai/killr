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
    m = memoise(lambda x: x)
    before = has_cache(m)(1)
    m(1)
    after = has_cache(m)(1)
    return [int(before), int(after)]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
