import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/tzdb")
from tzdb.tzdb_names import tzdb_names

tzdb_names()
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = tzdb_names()
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
print(f"py_ms {med * 1000:.17g}")
print("\n".join(result))
