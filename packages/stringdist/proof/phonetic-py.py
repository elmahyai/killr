import json
import statistics
import sys
import time
import warnings

warnings.filterwarnings("ignore")

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.phonetic import phonetic


def one():
    names = [
        "Robert",
        "rupert",
        "Rubin",
        "Ashcraft",
        "asHCroft",
        "Tymczak",
        "Pfister",
        "gutierrez",
        "Jackson",
        "washington",
        "Lee",
        None,
    ]
    parts = [
        phonetic(names, "soundex"),
        phonetic(names, "soundex", useBytes=True),
        phonetic(["Euler", "Ellery", "Gauss"]),
        phonetic(["Euler", "Ellery", "Gauss"], useBytes=True),
        phonetic([None, "abc"]),
        phonetic(""),
        phonetic("Mot\u00f6rhead"),
        phonetic("Mot\u00f6rhead", useBytes=True),
        phonetic("\rhello"),
        phonetic("Ashcraft", method="s"),
    ]
    out = []
    for part in parts:
        out.extend(part)
    return out


def fmt(value):
    if isinstance(value, str):
        return json.dumps(value)
    if value is None:
        return "null"
    if value != value:
        return '"NaN"'
    if value == float("inf"):
        return '"Inf"'
    if value == float("-inf"):
        return '"-Inf"'
    return format(float(value), ".17g")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
text = ",".join(fmt(item) for item in value)
print('{"value":[%s],"median_ms":%.17g}' % (text, statistics.median(elapsed)))
