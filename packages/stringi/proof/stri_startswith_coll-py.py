import json
import statistics
import time
from pathlib import Path

from stringi._na import NA
from stringi.coll import stri_startswith_coll


def canon(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [canon(item) for item in value]
    return value


STRINGS = ["Straße", "aßaßa", "aaa", "éÉe", "a-b.c", "chladný", "\ufb00\ufb00\ufb00\ufb00", "Yyý"] * 50
PATTERNS = ["ss", "ss", "aa", "e", "abc", "y", "ff", "y"]


def one():
    return stri_startswith_coll(STRINGS, PATTERNS, strength=1, locale="de")


OUT = Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_startswith_coll-python.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text('stri_startswith_coll("ßx", "ss", strength=1, locale="de") returns TRUE.' + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": canon(value), "median_ms": statistics.median(elapsed)}, ensure_ascii=False, separators=(",", ":")))
