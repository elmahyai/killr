import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.extract import str_extract_all
from stringr.pattern import boundary, fixed


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, dict):
        return {key: canon(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def show(groups):
    blocks = []
    for index, values in enumerate(groups, start=1):
        shown = " ".join("NA" if is_na(value) else value for value in values)
        blocks.append(f"[[{index}]] {shown}")
    return "\n".join(blocks)


shopping_list = ["apples x4", "bag of flour", "bag of sugar", "milk x2"]
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_extract_all-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(show(str_extract_all(shopping_list, "[a-z]+")) + "\n", encoding="utf-8")


def one():
    shopping = ["apples x4", "bag of flour", "bag of sugar", "milk x2", NA, ""] * 50
    return {
        "words": str_extract_all(shopping, "[a-z]+"),
        "digits": str_extract_all(shopping, r"\d"),
        "simple": str_extract_all(shopping, r"\b[a-z]+\b", simplify=True),
        "none": str_extract_all(["a", "b"], "z", simplify=True),
        "bound": str_extract_all(["This is, suprisingly, a sentence."] * 15, boundary("word")),
        "fixed": str_extract_all(["x.x."] * 20, fixed(".")),
        "empty": str_extract_all(["a b c"] * 15, ""),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
