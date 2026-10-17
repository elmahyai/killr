import json
import statistics
import time

from stringi._na import NA, is_na
from stringr.pattern import fixed
from stringr.replace import str_remove_all, str_replace_all


def upper(match):
    return [NA if is_na(item) else item.upper() for item in match]


def enc(value):
    if is_na(value):
        return None
    if isinstance(value, dict):
        return {key: enc(item) for key, item in value.items()}
    if isinstance(value, list):
        return [enc(item) for item in value]
    return value


fruits = ["one apple", "two pears", "three bananas"]
rows = str_remove_all(fruits, "[aeiou]")
out = "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_remove_all-python.txt"
open(out, "w", encoding="utf-8").write("\n".join(str(item) for item in rows) + "\n")

bulk = fruits * 200


def one():
    return {
        "all": str_remove_all(fruits, "[aeiou]"),
        "via": str_replace_all(fruits, "[aeiou]", ""),
        "upper": str_replace_all("abc", "a|c", upper),
        "removed": str_remove_all("abc", "a|c"),
        "fixed": str_remove_all("x.x.", fixed(".")),
        "long": str_remove_all(bulk, "[aeiou]"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": enc(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
