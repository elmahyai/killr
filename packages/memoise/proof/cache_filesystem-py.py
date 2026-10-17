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
    td = tempfile.mkdtemp(prefix="mc")
    fs = cache_filesystem(td)
    fs.set("abc", 4)
    got = fs.get("abc")
    has = fs.has_key("abc")
    fs.drop_key("abc")
    has2 = fs.has_key("abc")
    fs.set("a", 1)
    fs.reset()
    return [got, int(has), int(has2), len(fs.keys())]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
