import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.sub import stri_sub_all_replace


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    return {
        "from0": stri_sub_all_replace("hello", from_=0, length=3, replacement="Q"),
        "neg": stri_sub_all_replace("hello", from_=2, length=-3, replacement="XX"),
        "pieces": stri_sub_all_replace(
            "a b c", from_=[1, 3, 5], to=[1, 3, 5], replacement=["A", "B", "C"]
        ),
        "omit": stri_sub_all_replace(
            "abcdef", from_=[1, NA], to=[2, 4], replacement=["A", "B"], omit_na=True
        ),
        "keep_na": stri_sub_all_replace(
            "abcdef", from_=[1, NA], to=[2, 4], replacement=["A", "B"]
        ),
    }


Path(
    "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_sub_all_replace-python.txt"
).write_text(
    'stri_sub_all_replace("hello", from = 0, length = 3, replacement = "Q") returns Qlo.\n',
    encoding="utf-8",
)

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
