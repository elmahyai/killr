import statistics
import time

from r_yaml import as_yaml, verbatim_logical
from r_yaml.types import Vector

def one():
    text = as_yaml(Vector([True, False], "logical"), handlers={"logical": verbatim_logical})
    return text.rstrip("\n").replace("\n", "|")

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
