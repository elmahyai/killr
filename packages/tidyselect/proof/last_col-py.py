import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tidyselect.helpers_misc import last_col

vars = [f"v{i}" for i in range(1, 10001)]


def one():
    return last_col(5, vars)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

names = ["mpg", "cyl", "disp", "hp", "drat", "wt", "qsec", "vs", "am", "gear", "carb"]
example = last_col(5, names)
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "last_col-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'last_col(5, c("mpg", "cyl", "disp", "hp", "drat", "wt", "qsec", "vs", "am", "gear", "carb")) returns '
    + str(example)
    + ".\n",
    encoding="utf-8",
)

print("VALUE " + str(value))
print(f"MS {statistics.median(elapsed):.17g}")
