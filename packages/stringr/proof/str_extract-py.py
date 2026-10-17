import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringr.extract import str_extract
from stringr.pattern import boundary, coll, fixed, regex


def canon(value):
    if value is NA or value is None:
        return None
    if isinstance(value, dict):
        return {key: canon(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


def show(values):
    return " ".join("NA" if is_na(value) else value for value in values)


shopping_list = ["apples x4", "bag of flour", "bag of sugar", "milk x2"]
out = Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_extract-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
shown = show(str_extract(shopping_list, "([a-z]+) of ([a-z]+)", group=1))
out.write_text(shown + "\n", encoding="utf-8")


def one():
    shopping = ["apples x4", "bag of flour", "bag of sugar", "milk x2", NA, ""] * 70
    return {
        "digit": str_extract(shopping, r"\d"),
        "word": str_extract(shopping, "[a-z]+"),
        "group1": str_extract(shopping, "([a-z]+) of ([a-z]+)", group=1),
        "group2": str_extract(shopping, "([a-z]+) of ([a-z]+)", group=2),
        "fixed": str_extract(["x.x", "ab"] * 40, fixed(".")),
        "coll": str_extract(["\u0131", "I"], coll("I", ignore_case=True, locale="tr")),
        "empty": str_extract(["a b c"] * 20, ""),
        "bound": str_extract(["a b c"] * 40, boundary("word")),
        "casefold": str_extract(["Cat", "dog"] * 20, regex("[a-z]+", ignore_case=True)),
        "both": str_extract("abc", "(a)", group=[1, 0]),
        "empty_in": str_extract([], "a"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
