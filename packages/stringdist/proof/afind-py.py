import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.afind import afind


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


def numeric_part(result):
    return column_major(result["location"]) + column_major(result["distance"])


def one():
    texts = [
        "When I grow up, I want to be",
        "one of the harvesters of the sea",
        "I think before my days are gone",
        "I want to be a fisherman",
    ]
    patterns = ["fish", "gone", "to be"]
    parts = [
        numeric_part(afind(texts, patterns, method="running_cosine", q=3)),
        numeric_part(afind("abcabc", "bc", method="osa")),
        numeric_part(afind("aaaa", "aa", method="osa")),
        numeric_part(afind("Motörhead", "tor", useBytes=True, method="osa")),
        numeric_part(afind("Motörhead", "tor", useBytes=False, method="osa")),
        numeric_part(afind([None, "abc"], "bc", method="osa")),
        numeric_part(afind("abcdef", ["bc", "de"], method="osa")),
        numeric_part(afind("survey", "surgery", method="jw", p=0.1)),
        numeric_part(afind("ab", "ba", method="hamming")),
        numeric_part(afind("abc", "cba", method="cosine", q=2)),
        numeric_part(
            afind(texts, patterns, method="running_cosine", q=3, value=False)
        ),
    ]
    out = []
    for part in parts:
        out.extend(part)
    return out


def fmt(value):
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
