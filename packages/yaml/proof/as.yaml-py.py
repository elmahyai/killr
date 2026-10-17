import statistics
import time

from r_yaml import as_yaml
from r_yaml.types import Vector

value = {
    "foo": Vector(list(range(1, 11)), "integer"),
    "bar": Vector(["test1", "test2"], "character"),
}

def one():
    return as_yaml(value).rstrip("\n").replace("\n", "|")

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
