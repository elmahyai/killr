import json
import os
import statistics
import tempfile
import time

from remotes.deps import local_package_deps

directory = tempfile.mkdtemp()
with open(os.path.join(directory, "DESCRIPTION"), "w", encoding="utf-8") as handle:
    handle.write(
        "Package: toy\n"
        "Version: 0.0.1\n"
        "Depends: R (>= 3.0.0), stats\n"
        "Imports: remotes (>= 2.5.0),\n"
        "    cli (>= 3.0.0)\n"
        "LinkingTo: Rcpp\n"
        "Suggests: testthat (>= 3.0.0)\n"
    )


def one():
    return local_package_deps(directory)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
