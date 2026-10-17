import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringi.collate import stri_sort

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
        "main": stri_sort(left),
        "pl": stri_sort(["hladny", "chladny"], locale="pl_PL"),
        "sk": stri_sort(["hladny", "chladny"], locale="sk_SK"),
        "num": stri_sort([1, 100, 2, 101, 11, 10], numeric=True),
        "lex": stri_sort([1, 100, 2, 101, 11, 10]),
        "drop": stri_sort(["b", NA, "a"]),
        "last": stri_sort(["b", NA, "a"], na_last=True),
        "first": stri_sort(["b", NA, "a"], na_last=False, decreasing=True),
        "dec": stri_sort(["a", "a", "b"], decreasing=True),
        "french": stri_sort(["cote", "coté", "côte", "côté"], locale="en_US", french=True),
        "doubles": stri_sort([1e5, 2, 10, 1e-4]),
    }

Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_sort-python.txt").write_text("stri_sort([\"hladny\", \"chladny\"], locale=\"pl_PL\") returns chladny, hladny." + "\n", encoding="utf-8")
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
