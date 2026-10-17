import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringi.collate import stri_coll

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
    empty = stri_coll()
    num = stri_coll(numeric=True)
    full = stri_coll(
        locale="pl_PL",
        strength=1,
        alternate_shifted=True,
        french=True,
        uppercase_first=NA,
        case_level=True,
        normalization=True,
    )
    alias = stri_coll(normalisation=True)
    return {
        "empty_n": [len(empty)],
        "num_numeric": [num["numeric"]],
        "full_locale": [full["locale"]],
        "full_strength": [full["strength"]],
        "full_alternate": [full["alternate_shifted"]],
        "full_french": [full["french"]],
        "full_upper": [full["uppercase_first"]],
        "full_case": [full["case_level"]],
        "full_norm": [full["normalization"]],
        "alias_norm": [alias["normalization"]],
    }

Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_coll-python.txt").write_text("stri_coll(numeric=True) returns numeric True." + "\n", encoding="utf-8")
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
