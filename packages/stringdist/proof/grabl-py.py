import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.grabl import grabl


def one():
    texts = [
        "When I grow up, I want to be",
        "one of the harvesters of the sea",
        "I think before my days are gone",
        "I want to be a fisherman",
    ]
    return (
        grabl(texts, "fish", maxDist=0.5)
        + grabl(texts, "gone", maxDist=float("inf"))
        + grabl(texts, "grew", maxDist=1)
        + grabl("abcabc", "bc", maxDist=0)
        + grabl("abcabc", "bc", maxDist=1)
        + grabl([None, "abc"], "bc", maxDist=1)
        + grabl("Motörhead", "tor", useBytes=True, maxDist=2, method="osa")
        + grabl("abcdef", "bcd", method="lv", maxDist=1)
        + grabl("ab", "ba", method="hamming", maxDist=2)
        + grabl("abc", "cba", method="cosine", q=2, maxDist=1)
        + grabl("foo", "")
        + grabl("foo", None)
        + grabl(None, "foo")
        + grabl("", "foo", maxDist=3)
    )


# Flags are numeric so max_abs_diff applies: True = 1, False = 0, None = null.
def fmt_flag(value):
    if value is None:
        return "null"
    return "1" if value else "0"


result = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flag_text = ",".join(fmt_flag(item) for item in result)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (flag_text, statistics.median(elapsed))
)
