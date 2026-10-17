import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringi.collate import stri_duplicated_any

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

ids = [f"k{i}" for i in range(1, 2501)]


def one():
    return {
        "main": stri_duplicated_any(ids),
        "hit": stri_duplicated_any(["a", "b", "a", NA, "a", NA]),
        "last": stri_duplicated_any(["a", "b", "a", NA, "a", NA], from_last=True),
        "empty": stri_duplicated_any([]),
    }

Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_duplicated_any-python.txt").write_text("stri_duplicated_any([\"a\", \"b\", \"a\"]) returns 3." + "\n", encoding="utf-8")
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
