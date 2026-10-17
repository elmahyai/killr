import statistics
import tempfile
import time
from pathlib import Path

from r_yaml import yaml_load_file

path = tempfile.mktemp(suffix=".yml")
Path(path).write_text("- hey\n- hi\n- hello\n", encoding="utf-8")

def one():
    return ",".join(yaml_load_file(path))

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
