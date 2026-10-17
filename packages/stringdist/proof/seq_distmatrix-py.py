import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.seq_distmatrix import seq_distmatrix

seqs = [
    [1, 2, 3],
    [2, 3, 4],
    [1, 2, 1],
    [5, 6, 7, 8],
    [1, 0, 3],
    [2, 1],
    [1, 3, 2],
    [10, 11, 12],
]
short = seqs[:4]


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
    parts = [
        column_major(seq_distmatrix(short, short[1:4], method="osa")),
        column_major(
            seq_distmatrix(
                short,
                short[1:4],
                method="dl",
                weight=(0.5, 0.8, 0.3, 0.4),
            )
        ),
        column_major(seq_distmatrix(short, short[1:4], method="jw", p=0.1)),
        column_major(seq_distmatrix(short, short[1:4], method="cosine", q=2)),
        column_major(
            seq_distmatrix(
                [[1, 2], [1, 2, 3]],
                [[2, 1], [1, 2, 3]],
                method="hamming",
            )
        ),
        column_major(seq_distmatrix([None, [1, 2]], [[1, 2], [3, 4]])),
        column_major(seq_distmatrix([], [[1, 2]])),
        list(seq_distmatrix(short, method="osa")),
        list(seq_distmatrix(short[:3], method="lcs")),
        column_major(
            seq_distmatrix(
                [[1, 2, 3], [4, 5, 6]],
                [[1, 2, 3], [4, 5, 6]],
                weight=(0.5, 1, 1, 1),
            )
        ),
        column_major(
            seq_distmatrix(
                {"x": [1, 2, 3], "y": [2, 3, 4]},
                {"x": [1, 2, 3], "y": [2, 3, 4]},
                useNames="names",
            )
        ),
        column_major(seq_distmatrix([[1, 2, 3]], [[2, 3, 4]])),
        list(seq_distmatrix([1, 2, 3])),
        column_major(
            seq_distmatrix(
                [[1, None, 3]],
                [[1, 2, 3]],
                method="osa",
            )
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
