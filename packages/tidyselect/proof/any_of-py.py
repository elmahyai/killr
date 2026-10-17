import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tidyselect.helpers_vector import any_of

vars = [f"v{i}" for i in range(1, 10001)]
rev = [f"v{i}" for i in range(10000, 0, -1)]
wanted = rev + rev + [f"missing{i}" for i in range(1, 101)]


def one():
    return any_of(wanted, vars=vars)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

iris = ["Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species"]
example = any_of(["Sepal.Length", "not_there", "Sepal.Width"], vars=iris)
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "any_of-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'with_vars(c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species"), any_of(c("Sepal.Length", "not_there", "Sepal.Width"))) returns '
    + ", ".join(str(item) for item in example)
    + ".\n",
    encoding="utf-8",
)

print("VALUE " + ",".join(str(item) for item in value))
print(f"MS {statistics.median(elapsed):.17g}")
