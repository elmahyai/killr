import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.seq_ain import seq_ain


def utf8_codes(text):
    return [ord(ch) for ch in text]


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
    x = [[1, 2, 3], [3, 2, 1], [1, 3, 4]]
    table = [[5, 3, 1, 2], [1, 2, 3, 4]]
    return flatten(
        [
            as_num(seq_ain(x, table, maxDist=2)),
            as_num(seq_ain(x, table, maxDist=0.5)),
            as_num(
                seq_ain([[1, 2, 3]], [[2, 1, 3]], method="osa", maxDist=2)
            ),
            as_num(
                seq_ain([[1, 2, 3]], [[2, 1, 3]], method="lv", maxDist=2)
            ),
            as_num(seq_ain([[2, 1]], [[1, 3, 2]], method="dl", maxDist=3)),
            as_num(
                seq_ain([[1, 2, 3]], [[1, 0, 3]], method="hamming", maxDist=2)
            ),
            as_num(
                seq_ain([[1, 2, 3]], [[1, 0, 3]], method="lcs", maxDist=2)
            ),
            as_num(
                seq_ain(
                    [[1, 2, 3]],
                    [[1, 0, 3]],
                    method="qgram",
                    q=2,
                    maxDist=1,
                )
            ),
            as_num(
                seq_ain(
                    [[1, 2, 3]],
                    [[1, 0, 3]],
                    method="cosine",
                    q=2,
                    maxDist=1,
                )
            ),
            as_num(
                seq_ain(
                    [[1, 2, 3]],
                    [[1, 0, 3]],
                    method="jaccard",
                    q=2,
                    maxDist=1,
                )
            ),
            as_num(
                seq_ain(
                    [utf8_codes("martha")],
                    [utf8_codes("marhta")],
                    method="jw",
                    maxDist=0.2,
                )
            ),
            as_num(seq_ain([[1, 2, 3]], [[2, 3, 4]], maxDist=2)),
            as_num(seq_ain([[3.14, 1]], [[3, 1]], maxDist=1)),
            as_num(seq_ain([None], [[1, 2]], maxDist=2)),
            as_num(
                seq_ain(
                    [[1, None, 3], None],
                    [[1, 2, 3]],
                    maxDist=1,
                )
            ),
            as_num(
                seq_ain(
                    [[1, None, 3], None],
                    [[1, 2, 3]],
                    maxDist=1,
                    matchNA=False,
                )
            ),
            as_num(
                seq_ain([[1, 2]], [[1, 2, 3], [4, 5, 6]], maxDist=1)
            ),
            as_num(seq_ain([[1, 2, 3]], [[2, 1, 3]], maxDist=float("inf"))),
            as_num(
                seq_ain(
                    [[1, 2, 3]],
                    [[2, 1, 3]],
                    weight=(0.5, 1, 1, 1),
                    maxDist=2,
                )
            ),
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
