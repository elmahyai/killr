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
    cm = cache_memory()
    cm.set("k", 7)
    got = cm.get("k")
    has = cm.has_key("k")
    cm.drop_key("k")
    has2 = cm.has_key("k")
    cm.set("a", 1)
    cm.reset()
    return [got, int(has), int(has2), len(cm.keys())]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
