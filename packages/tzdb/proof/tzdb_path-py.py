import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/tzdb")
from tzdb.tzdb_path import tzdb_path

tzdb_path("text")
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = tzdb_path("text")
    elapsed.append(time.perf_counter() - t0)
med = statistics.median(elapsed)
try:
    tzdb_path("binary")
    err = ""
except ValueError as exc:
    err = str(exc)
version = (Path(result) / "version").read_text(encoding="utf-8").splitlines()[0]
files = sorted(path.name for path in Path(result).iterdir() if path.is_file())
print(f"py_ms {med * 1000:.17g}")
print(err)
print(version)
print("\n".join(files))
