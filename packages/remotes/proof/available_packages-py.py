import json
import statistics
import time

from remotes.available_packages import (
    available_packages,
    available_packages_reset,
    available_packages_set,
)

url = "https://cloud.r-project.org"
available_packages_reset()
db = available_packages(url, "source")
hit = db.rownames.index("remotes")
package = db["Package"][hit]
version = db["Version"][hit]
rowname = db.rownames[hit]
n = len(db)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    available_packages(url, "source")
    elapsed.append((time.perf_counter() - started) * 1000)

named = available_packages_set({"CRAN": url}, "source", {"Package": "other"})
if list(named.values()) != ["other"]:
    raise SystemExit("named repos collided with the unnamed key")
again = available_packages(url, "source")
if again["Version"][again.rownames.index("remotes")] != version or len(again) != n:
    raise SystemExit("cached database was replaced")

print(json.dumps({
    "package": package,
    "version": version,
    "rowname": rowname,
    "nrow": n,
    "median_ms": statistics.median(elapsed),
}))
