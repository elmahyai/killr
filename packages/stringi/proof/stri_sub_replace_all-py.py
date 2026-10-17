import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stringi._na import NA
from stringi.sub import stri_sub_replace_all


def join_words(values):
    parts = []
    for item in values:
        parts.append("NA" if item is NA else '"' + item + '"')
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def conv(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [conv(item) for item in value]
    return value


out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_sub_replace_all-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)

res = stri_sub_replace_all(
    "a b c", from_=[1, 3, 5], to=[1, 3, 5], replacement=["A", "B", "C"]
)
text = "stri_sub_replace_all(\"a b c\", c(1, 3, 5), c(1, 3, 5), replacement = c(\"A\", \"B\", \"C\")) returns " + join_words(res) + ".\n"


def one():
    return stri_sub_replace_all(
        ["a b c", "hello"] * 80,
        [[1, 3, 5], [1, 4]],
        [[1, 3, 5], [2, 5]],
        replacement=[["A", "B", "C"], ["X", "Y"]],
    )


out.write_text(text, encoding="utf-8")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": conv(value), "median_ms": statistics.median(elapsed)}))
