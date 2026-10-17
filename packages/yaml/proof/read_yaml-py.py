import statistics
import tempfile
import time
from pathlib import Path

from r_yaml import read_yaml

path = tempfile.mktemp(suffix=".yml")
Path(path).write_text("flag: y\noct: 015\n", encoding="utf-8")

def one():
    value = read_yaml(path)
    flag = "TRUE" if value["flag"] else "FALSE"
    return f"{flag},{value['oct']}"

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
