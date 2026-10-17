import json
import statistics
import time
from pathlib import Path

from stringi._na import NA, is_na
from stringi.collate import stri_cmp_lt

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
        "main": stri_cmp_lt(left, right),
        "short": stri_cmp_lt(["a", "b", "A", "\ufeffa", NA], ["b", "b", "a", "a", "a"]),
        "pl": stri_cmp_lt("hladny", "chladny", locale="pl_PL"),
        "sk": stri_cmp_lt("hladny", "chladny", locale="sk_SK"),
        "primary": stri_cmp_lt(["Mario", "mario", "Mário", "mário"], "mario", strength=1),
        "secondary": stri_cmp_lt(["Mario", "mario", "Mário", "mário"], "mario", strength=2),
        "cased": stri_cmp_lt(["Mario", "mario", "Mário", "mário"], "mario", strength=1, case_level=True),
        "numeric": stri_cmp_lt("number100", "number2", numeric=True),
        "shifted": stri_cmp_lt("above mentioned", "above-mentioned", alternate_shifted=True),
        "phone": stri_cmp_lt("Gärtner", "Gaertner", locale="de_DE@collation=phonebook", strength=1),
        "danish": stri_cmp_lt(["a", "A"], ["A", "a"], locale="da_DK"),
        "upper": stri_cmp_lt(["a", "A"], ["A", "a"], locale="da_DK", uppercase_first=NA),
        "french": stri_cmp_lt(["cote", "côte"], ["coté", "côté"], locale="en_US", french=True),
    }

Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_cmp_lt-python.txt").write_text("stri_cmp_lt([\"hladny\"], [\"chladny\"], locale=\"sk_SK\") returns TRUE." + "\n", encoding="utf-8")
value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
