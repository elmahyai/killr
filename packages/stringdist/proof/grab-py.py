import json
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.grab import grab


def one():
    texts = [
        "When I grow up, I want to be",
        "one of the harvesters of the sea",
        "I think before my days are gone",
        "I want to be a fisherman",
    ]
    idx = [
        float(i)
        for i in (
            grab(texts, "fish", maxDist=0.5)
            + grab(texts, "gone", maxDist=float("inf"))
            + grab(texts, "grew", maxDist=1)
            + grab("abcabc", "bc", maxDist=0)
            + grab("abcabc", "bc", maxDist=1)
            + grab([None, "abc"], "bc", maxDist=1)
            + grab("Motörhead", "tor", useBytes=True, maxDist=2, method="osa")
            + grab("abcdef", "bcd", method="lv", maxDist=1)
            + grab("ab", "ba", method="hamming", maxDist=2)
            + grab("abc", "cba", method="cosine", q=2, maxDist=1)
        )
    ]
    strings = grab(texts, "fish", maxDist=0.5, value=True) + grab(
        texts, "to be", method="running_cosine", q=3, maxDist=0.2, value=True
    )
    return {"idx": idx, "strings": strings}


def fmt_num(value):
    if value is None:
        return "null"
    if value != value:
        return '"NaN"'
    if value == float("inf"):
        return '"Inf"'
    if value == float("-inf"):
        return '"-Inf"'
    return format(float(value), ".17g")


result = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
num_text = ",".join(fmt_num(item) for item in result["idx"])
str_text = ",".join(json.dumps(item) for item in result["strings"])
print(
    '{"value":[%s],"strings":[%s],"median_ms":%.17g}'
    % (num_text, str_text, statistics.median(elapsed))
)
