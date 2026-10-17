import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tidyselect.helpers_vector import all_of

vars = [f"v{i}" for i in range(1, 10001)]
wanted = [f"v{i}" for i in range(10000, 0, -1)]


def one():
    return all_of(wanted, vars)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

iris = ["Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species"]
example = all_of(["Sepal.Length", "Sepal.Width"], iris)
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "all_of-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'with_vars(c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species"), all_of(c("Sepal.Length", "Sepal.Width"))) returns '
    + ", ".join(str(item) for item in example)
    + ".\n",
    encoding="utf-8",
)

print("VALUE " + ",".join(str(item) for item in value))
print(f"MS {statistics.median(elapsed):.17g}")
