import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.stringdistmatrix import stringdistmatrix

words = [
    "ca", "abc", "MARTHA", "MATHRA", "survey", "surgery",
    "leia", "leela", "crate", "trace", "dixon", "dicksonx",
    "john doe", "jane doe", "sock", "sck", "Euler", "Ellery",
    "Motörhead", "Motorhead", "abcabc", "aaa", "hello", "HeLl0",
    "DHCXXXXX", "HCDXXXXX", "RICK WARREN", "WARREN BUFFET",
    "", "a",
]
short = words[:8]


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
        column_major(stringdistmatrix(short, short[2:5], method="osa")),
        column_major(
            stringdistmatrix(
                short,
                short[2:5],
                method="dl",
                weight=(0.5, 0.8, 0.3, 0.4),
            )
        ),
        column_major(stringdistmatrix(short, short[2:5], method="jw", p=0.1)),
        column_major(stringdistmatrix(short, short[2:5], method="cosine", q=2)),
        column_major(
            stringdistmatrix(["ab", "abc"], ["ba", "abc"], method="hamming")
        ),
        column_major(stringdistmatrix(["a", None, "b"], ["aa", "bb", "b"])),
        column_major(stringdistmatrix([], ["a", "b"])),
        list(stringdistmatrix(short, method="osa")),
        list(stringdistmatrix(short[:4], method="lcs")),
        list(stringdistmatrix(["Euler", "Ellery", "Gauss"], method="soundex")),
        list(
            stringdistmatrix(
                ["Motörhead", "Motorhead"],
                method="dl",
                useBytes=True,
            )
        ),
        column_major(
            stringdistmatrix(
                ["ca", "abc"],
                ["abc", "ca"],
                weight=(0.5, 1, 1, 1),
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
