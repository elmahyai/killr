import json
import os
import statistics
import tempfile
import time

from remotes.deps import dev_package_deps

directory = tempfile.mkdtemp()
with open(os.path.join(directory, "DESCRIPTION"), "w", encoding="utf-8") as handle:
    handle.write("Package: toydeps\nVersion: 0.0.1\nImports: remotes\n")


def one():
    return dev_package_deps(
        directory, repos="https://cloud.r-project.org", type="source"
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
