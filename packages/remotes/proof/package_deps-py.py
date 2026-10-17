import json
import statistics
import time

from remotes.deps import package_deps


def one():
    return package_deps(
        "remotes", repos="https://cloud.r-project.org", type="source"
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
