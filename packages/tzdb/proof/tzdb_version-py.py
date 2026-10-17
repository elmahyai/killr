import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/tzdb")
from tzdb.tzdb_version import tzdb_version

tzdb_version()
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = tzdb_version()
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print(result)
