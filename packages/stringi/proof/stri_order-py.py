import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringi.collate import stri_order

base = [
    'hladny',
    'chladny',
    'Mario',
    'mario',
    'Mário',
    'mário',
    'number2',
    'number100',
    'a',
    'A',
    'b',
    'B',
    NA,
    '',
    'NA',
    '\ufeffabc',
    'abc',
    'ą',
    'ff',
    'ﬀ',
    'cote',
    'côte',
    'coté',
    'côté',
    'Gärtner',
    'Gaertner',
    'above mentioned',
    'above-mentioned',
    '10',
    '2',
    '100',
    'ß',
    'groß',
    'GROSS',
]
left = base * 50
right = base[::-1] * 50


def plain(value):
    if value is NA or is_na(value):
        return None
    if isinstance(value, bytes):
        return list(value)
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value

def one():
    return {
        "main": stri_order(left),
        "pl": stri_order(["hladny", "chladny"], locale="pl_PL"),
        "sk": stri_order(["hladny", "chladny"], locale="sk_SK"),
        "num": stri_order([1, 100, 2, 101, 11, 10], numeric=True),
        "drop": stri_order(["b", NA, "a", NA], na_last=NA),
        "first": stri_order(["b", NA, "a", NA], na_last=False),
        "dec": stri_order(["a", "a", "b"], decreasing=True),
        "ties": stri_order(["a", "\u0105", "a\u0328", "b"], strength=1),
    }

Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_order-python.txt").write_text("stri_order([\"hladny\", \"chladny\"], locale=\"pl_PL\") returns 2, 1." + "\n", encoding="utf-8")
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
