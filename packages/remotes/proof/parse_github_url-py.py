import json
import statistics
import time

from remotes.parse import parse_github_url


def one():
    return parse_github_url(
        "https://github.com/r-lib/remotes/releases/tag/1.0.0"
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
