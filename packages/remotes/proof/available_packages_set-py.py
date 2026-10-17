import json
import statistics
import time

from remotes.available_packages import available_packages_reset, available_packages_set

url = "https://cran.r-project.org"
db = {"Package": "digest", "Version": "0.6.37"}


def one():
    return available_packages_set(url, "source", db)


available_packages_reset()
value = one()
elapsed = []
for _ in range(20):
    available_packages_reset()
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

second = available_packages_set(
    url, "source", {"Package": "digest", "Version": "9"}
)
if list(second.values()) != ["digest", "0.6.37"]:
    raise SystemExit("second insert replaced the cached database")

available_packages_reset()
fresh = available_packages_set(
    url, "source", {"Package": "digest", "Version": "9"}
)
if list(fresh.values()) != ["digest", "9"]:
    raise SystemExit("reset did not allow a new database")
held = available_packages_set(
    url, "source", {"Package": "digest", "Version": "0"}
)
if list(held.values()) != ["digest", "9"]:
    raise SystemExit("new database was replaced")

named = available_packages_set({"CRAN": url}, "source", {"Package": "other"})
if list(named.values()) != ["other"]:
    raise SystemExit("named repos collided with the unnamed key")
unnamed_again = available_packages_set(url, "source", {"Package": "nope"})
if list(unnamed_again.values()) != ["digest", "9"]:
    raise SystemExit("unnamed key was replaced by the named repos insert")

available_packages_reset()
null_db = available_packages_set(url, "source", None)
replaced = available_packages_set(url, "source", {"Package": "after-null"})
if null_db is not None or list(replaced.values()) != ["after-null"]:
    raise SystemExit("a stored None was kept")

print(json.dumps({
    "names": list(value.keys()),
    "values": list(value.values()),
    "median_ms": statistics.median(elapsed),
}))
