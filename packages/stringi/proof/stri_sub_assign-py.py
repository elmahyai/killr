import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stringi._na import NA
from stringi.sub import stri_sub_assign


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


out = Path(__file__).resolve().parents[1] / "docs" / "output" / "stri_sub<--python.txt"
out.parent.mkdir(parents=True, exist_ok=True)

res = stri_sub_assign(
    ["spam, spam, bacon, and spam", "eggs and spam"], from_=1, to=4, value="stringi"
)
text = "stri_sub<-(c(\"spam, spam, bacon, and spam\", \"eggs and spam\"), 1, 4, value = \"stringi\") returns " + join_words(res) + ".\n"


def one():
    return stri_sub_assign(
        ["hello", "world", "", NA] * 80,
        from_=[1, -2, 5, 1],
        to=[2, -1, 6, 1],
        value=["XX", "Y", "Z", "Q"],
    )


out.write_text(text, encoding="utf-8")
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": conv(value), "median_ms": statistics.median(elapsed)}))
