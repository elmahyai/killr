import json
import statistics
import time

from stringi._na import NA, is_na
from stringr.pattern import coll, fixed
from stringr.replace import str_replace


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = list(names)


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
rows = []
rows.extend(str_replace(fruits, "[aeiou]", "-"))
rows.extend(str_replace(fruits, "([aeiou])", "\\1\\1"))
rows.extend(str_replace(fruits, "[aeiou]", ["1", "2", "3"]))
rows.extend(str_replace(fruits, ["a", "e", "i"], "-"))
out = "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_replace-python.txt"
open(out, "w", encoding="utf-8").write("\n".join("" if item is None else str(item) for item in rows) + "\n")

bulk = fruits * 400
named_in = Named(["3", "2", "1"], ["C", "B", "A"])


def one():
    named = str_replace(named_in, "[0-9]", "x")
    return {
        "dash": str_replace(fruits, "[aeiou]", "-"),
        "back": str_replace(fruits, "([aeiou])", "\\1\\1"),
        "vec": str_replace(fruits, "[aeiou]", ["1", "2", "3"]),
        "pat": str_replace(fruits, ["a", "e", "i"], "-"),
        "fixed": str_replace("x.x", fixed("."), "Y"),
        "coll": str_replace("\u0131", coll("I", ignore_case=True, locale="tr"), "Y"),
        "na": str_replace("xx", "x", NA),
        "fun": str_replace("abc", "a|c", upper),
        "fun_na": str_replace("abc", "b", lambda xs: [NA for _ in xs]),
        "zero": str_replace("abc", "$", upper),
        "empty_pat": str_replace("abc", "", upper),
        "num": str_replace([1, 12], "1", "X"),
        "names": list(named.names),
        "named_values": list(named),
        "long": str_replace(bulk, "[aeiou]", "-"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": enc(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
