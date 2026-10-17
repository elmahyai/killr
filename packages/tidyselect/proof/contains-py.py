import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tidyselect.helpers_contains import contains

vars = [f"Var{i}" for i in range(1, 10001)]


def one():
    return contains(["00", "99"], vars=vars)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

iris = ["Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species"]
example = contains("al", vars=iris)
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "contains-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'contains("al", vars = c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species")) returns '
    + ", ".join(str(item) for item in example)
    + ".\n",
    encoding="utf-8",
)

print("VALUE " + ",".join(str(item) for item in value))
print(f"MS {statistics.median(elapsed):.17g}")
