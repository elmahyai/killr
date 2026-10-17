import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.qgrams import qgrams


def flat_q(matrix):
    if not matrix.data:
        return []
    nrows = len(matrix.data)
    ncols = len(matrix.data[0]) if nrows and matrix.data[0] else 0
    out = []
    for col in range(ncols):
        for row in range(nrows):
            out.append(matrix.data[row][col])
    return out


def fp_colnames(matrix):
    names = matrix.colnames
    if not names:
        return [0.0, 0.0]
    return [
        float(len(names)),
        float(sum(sum(ord(ch) for ch in name) for name in names)),
    ]


def one():
    return flatten(
        [
            flat_q(qgrams("a", "b", q=1)),
            flat_q(qgrams("aa", q=1)),
            flat_q(qgrams(["a", "a"], q=1)),
            flat_q(qgrams([None, "a"], q=1)),
            flat_q(qgrams(None, q=1)),
            flat_q(qgrams(["a", "ab"], q=2)),
            flat_q(qgrams(["a"], q=2)),
            flat_q(qgrams([""], q=0)),
            flat_q(qgrams("Motörhead", "Motorhead", q=2)),
            flat_q(
                qgrams(
                    "Motörhead",
                    "Motorhead",
                    q=2,
                    useBytes=True,
                    useNames=True,
                )
            ),
            fp_colnames(
                qgrams(
                    "Motörhead",
                    "Motorhead",
                    q=2,
                    useBytes=True,
                    useNames=True,
                )
            ),
            flat_q(qgrams("abc", "cba", q=2, useNames=True)),
            fp_colnames(qgrams("abc", "cba", q=2, useNames=True)),
            [float(len(qgrams().data)), float(len(qgrams().data[0]) if qgrams().data else 0)],
            [
                float(len(qgrams(None, q=1).data)),
                float(
                    len(qgrams(None, q=1).data[0])
                    if qgrams(None, q=1).data
                    else 0
                ),
            ],
        ]
    )


def flatten(parts):
    out = []
    for part in parts:
        if isinstance(part, list):
            out.extend(flatten(part))
        else:
            out.append(part)
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
