import statistics
import tempfile
import time
from pathlib import Path

from r_yaml import write_yaml
from r_yaml.types import Vector

path = tempfile.mktemp(suffix=".yml")

def one():
    write_yaml({"foo": Vector([1, 2, 3], "integer")}, path)
    return "|".join(Path(path).read_text(encoding="utf-8").splitlines())

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
