import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tidyselect.starts_with import starts_with

vars = [f"v{i}" for i in range(1, 10001)]
match = ["V1", "v2", "zz", "V99"]


def one():
    return starts_with(match, vars=vars)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

iris = ["Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species"]
example = starts_with(["Petal", "Sepal"], vars=iris)
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "starts_with-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'starts_with(c("Petal", "Sepal"), vars = c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species")) returns '
    + ", ".join(str(item) for item in example)
    + ".\n",
    encoding="utf-8",
)

print("VALUE " + ",".join(str(item) for item in value))
print(f"MS {statistics.median(elapsed):.17g}")
