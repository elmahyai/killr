import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generics.set_helpers import is_element, setdiff, setequal, union


def encode(values):
    def one(value):
        if value is None:
            return "NA"
        if isinstance(value, float) and value != value:
            return "NaN"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        return format(value, ".17g") if isinstance(value, float) else str(value)

    return ",".join(one(value) for value in values)


def one():
    a = [3.0, None, float("nan"), 3.0, 1.0, None]
    b = [2.0, None, float("nan"), 2.0]
    return [
        "is.element=" + encode(is_element(a, b)),
        "setdiff=" + encode(setdiff(a, b)),
        "setequal=" + ("TRUE" if setequal(a, b) else "FALSE"),
        "union=" + encode(union(a, b)),
        "empty=" + encode(union([], [])),
        "chars=" + encode(union(["b", "a", "b"], ["a", "c"])),
        "logical=" + encode(is_element([True, False], [False])),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE")
print("\n".join(value))
print(f"MS {statistics.median(elapsed):.17g}")

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "set_helpers-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(value) + "\n")
