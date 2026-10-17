import json
import statistics
import time

from remotes.bioc import bioc_install_repos


def one():
    return bioc_install_repos(bioc_ver="3.6")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
