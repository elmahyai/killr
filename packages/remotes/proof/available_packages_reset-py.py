import json
import statistics
import time

from remotes.available_packages import available_packages_reset, available_packages_set

url = "https://cran.r-project.org"
db = {"Package": "digest", "Version": "0.6.37"}


def insert():
    return available_packages_set(url, "source", db)


def one():
    return available_packages_reset()


insert()
value = one()
elapsed = []
for _ in range(20):
    insert()
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

if value is not None:
    raise SystemExit("reset did not return None")
fresh = available_packages_set(url, "source", {"Package": "kept"})
if list(fresh.values()) != ["kept"]:
    raise SystemExit("reset did not clear the cache")

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
