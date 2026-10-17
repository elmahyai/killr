import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.ain import ain


def as_num(value):
    if isinstance(value, list):
        return [as_num(item) for item in value]
    if value is None:
        return None
    return 1.0 if value else 0.0


def flatten(parts):
    out = []
    for part in parts:
        if isinstance(part, list):
            out.extend(flatten(part))
        else:
            out.append(part)
    return out


def one():
    return flatten(
        [
            as_num(ain("leia", ["uhura", "leela"], maxDist=5)),
            as_num(ain("leia", ["uhura", "leela"], maxDist=1)),
            as_num(
                ain(
                    ["leia", "uhura"],
                    ["ripley", "leela", "scully", "trinity"],
                    maxDist=2,
                )
            ),
            as_num(ain("leia", ["uhura", "leela"], maxDist=float("inf"))),
            as_num(ain("leia", ["uhura", "leela"], maxDist=2)),
            as_num(ain("MARTHA", ["MATHRA", "MARHTA"], method="jw", maxDist=0.2)),
            as_num(ain("abc", ["cba", "abc"], method="osa", maxDist=2)),
            as_num(ain("ab", "ba", method="hamming", maxDist=2)),
            as_num(ain("Motörhead", "Motorhead", method="dl", maxDist=2)),
            as_num(
                ain(
                    "Motörhead",
                    "Motorhead",
                    method="dl",
                    useBytes=True,
                    maxDist=2,
                )
            ),
            as_num(ain([None, "abc"], ["aa", "bb", "b"], maxDist=2)),
            as_num(
                ain([None, "abc"], [None, "bb", "b"], maxDist=2, matchNA=False)
            ),
            as_num(ain("survey", ["surgery", "sunny"], method="lcs", maxDist=3)),
            as_num(ain("abc", "cba", method="cosine", q=2, maxDist=1)),
            as_num(ain("Euler", ["Ellery", "Gauss"], method="soundex", maxDist=1)),
        ]
    )


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
