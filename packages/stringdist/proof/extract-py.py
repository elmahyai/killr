import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.extract import extract


def column_major(mat):
    if not mat:
        return []
    nrow = len(mat)
    ncol = len(mat[0])
    out = []
    for j in range(ncol):
        for i in range(nrow):
            out.append(mat[i][j])
    return out


def one():
    texts = [
        "When I grow up, I want to be",
        "one of the harvesters of the sea",
        "I think before my days are gone",
        "I want to be a fisherman",
    ]
    parts = [
        column_major(extract(texts, "harvested", maxDist=3)),
        column_major(extract(texts, "fish", maxDist=0.5)),
        column_major(extract(texts, "gone", maxDist=float("inf"))),
        column_major(extract("abcabc", "bc", maxDist=0)),
        column_major(extract("abcabc", "bc", maxDist=1)),
        column_major(extract([None, "abc"], "bc", maxDist=1)),
        column_major(
            extract("Motörhead", "tor", useBytes=True, maxDist=2, method="osa")
        ),
        column_major(extract("abcdef", "bcd", method="lv", maxDist=1)),
        column_major(extract("ab", "ba", method="hamming", maxDist=2)),
        column_major(extract("abc", "cba", method="cosine", q=2, maxDist=1)),
        column_major(
            extract(texts, "to be", method="running_cosine", q=3, maxDist=0.2)
        ),
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
