import json
import statistics
import time

from stringi._na import NA, is_na
from stringr.replace import str_replace_na


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = list(names)


def enc(value):
    if is_na(value):
        return None
    if isinstance(value, dict):
        return {key: enc(item) for key, item in value.items()}
    if isinstance(value, list):
        return [enc(item) for item in value]
    return value


rows = str_replace_na([NA, "abc", "def"])
out = "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_replace_na-python.txt"
open(out, "w", encoding="utf-8").write("\n".join(str(item) for item in rows) + "\n")

bulk = ["test", NA] * 2000
named_in = Named([NA, "x"], ["A", "B"])


def one():
    named = str_replace_na(named_in)
    return {
        "basic": str_replace_na([NA, "abc", "def"]),
        "xx": str_replace_na([NA, "abc"], "xx"),
        "blank": str_replace_na([NA, "abc"], ""),
        "num": str_replace_na([1, NA, 2.5]),
        "logical": str_replace_na([True, NA, False]),
        "named_names": list(named.names),
        "named_values": list(named),
        "long": str_replace_na(bulk, "zz"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": enc(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
