import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.seq_qgrams import seq_qgrams


def flat_m(matrix):
    if not matrix.data:
        return []
    nrows = len(matrix.data)
    ncols = len(matrix.data[0]) if nrows and matrix.data[0] else 0
    out = []
    for col in range(ncols):
        for row in range(nrows):
            out.append(matrix.data[row][col])
    return out


def one():
    parts = [
        flat_m(seq_qgrams([1, 2, 3], [2, 3, 4], q=2)),
        flat_m(seq_qgrams([1, 2], q=1)),
        flat_m(seq_qgrams([1, None, 3], q=2)),
        flat_m(seq_qgrams([], [1, 2], q=1)),
        flat_m(seq_qgrams(None, q=1)),
        flat_m(seq_qgrams([1, 2], q=3)),
    ]
    empty = seq_qgrams()
    parts.append(
        [
            float(len(empty.data)),
            float(len(empty.data[0]) if empty.data else 0),
        ]
    )
    out = []
    for part in parts:
        if isinstance(part, list):
            out.extend(part)
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
