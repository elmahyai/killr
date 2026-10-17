import json
import statistics
import time

from stringi._na import NA, is_na
from stringr.pattern import boundary, coll, fixed
from stringr.replace import str_replace_all


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


def show(values):
    return [NA if is_na(item) else item for item in values]


fruits = ["one apple", "two pears", "three bananas"]
joined = "---".join(fruits)
rows = []
rows.extend(show(str_replace_all(fruits, "[aeiou]", "-")))
rows.extend(show(str_replace_all(fruits, "[aeiou]", upper)))
rows.extend(show(str_replace_all(fruits, "b", NA)))
rows.extend(show(str_replace_all(joined, {"one": "1", "two": "2", "three": "3"})))
out = "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_replace_all-python.txt"
open(out, "w", encoding="utf-8").write("\n".join(str(item) for item in rows) + "\n")

bulk = fruits * 200
bulk_fun = fruits * 80


def one():
    return {
        "dash": str_replace_all(fruits, "[aeiou]", "-"),
        "fun": str_replace_all(fruits, "[aeiou]", upper),
        "na": str_replace_all(fruits, "b", NA),
        "named": str_replace_all(joined, {"one": "1", "two": "2", "three": "3"}),
        "zero": str_replace_all("abc", "$|^", lambda xs: ["X"] * len(xs)),
        "bound": str_replace_all("x x", boundary("word"), upper),
        "empty_pat": str_replace_all("abc", "", upper),
        "fixed": str_replace_all("x.x.", fixed("."), "Y"),
        "coll": str_replace_all("\u0131I", coll("I", ignore_case=True, locale="tr"), "Y"),
        "multi": str_replace_all(["ab", "ba"], {"a": "A", "b": "B"}),
        "group": str_replace_all("abcde", "(b)(c)(d)", "\\2"),
        "na_fun": str_replace_all(["ab", NA, "c"], "a|c", upper),
        "long": str_replace_all(bulk, "[aeiou]", "-"),
        "long_fun": str_replace_all(bulk_fun, "[aeiou]", upper),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": enc(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
