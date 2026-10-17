import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/stringdist"]
from stringdist.amatch import amatch
from stringdist.seq_dist import seq_dist
from stringdist.stringdist import stringdist


def utf8_codes(text):
    return [ord(ch) for ch in text]


def as_num(value):
    if isinstance(value, list):
        return [as_num(item) for item in value]
    if value is None:
        return None
    return float(value)


def flatten(parts):
    out = []
    for part in parts:
        if isinstance(part, list):
            out.extend(flatten(part))
        else:
            out.append(part)
    return out


def one():
    words = ["ca", "abc", "MARTHA", "MATHRA", "survey", "surgery", "leia", "leela"]
    cross = []
    for i in range(4):
        left = words[i]
        right = words[i + 1]
        cross.extend(
            flatten(
                [
                    as_num(
                        seq_dist(
                            [utf8_codes(left)],
                            [utf8_codes(right)],
                            method="osa",
                        )
                    ),
                    as_num(stringdist(left, right, method="osa")),
                    as_num(amatch(left, right, maxDist=100, method="osa")),
                ]
            )
        )
    return flatten(
        [
            as_num(
                seq_dist(
                    [[1, 1, 2]],
                    [[1, 2, 1], [2, 3, 1, 2]],
                )
            ),
            as_num(
                seq_dist([[1, 2, 3]], [[2, 1, 3]], method="osa")
            ),
            as_num(seq_dist([[1, 2, 3]], [[2, 1, 3]], method="lv")),
            as_num(seq_dist([[2, 1]], [[1, 3, 2]], method="dl")),
            as_num(seq_dist([[1, 2, 3]], [[1, 0, 3]], method="hamming")),
            as_num(seq_dist([[1, 2, 3]], [[1, 0, 3]], method="lcs")),
            as_num(seq_dist([[1, 2, 3]], [[1, 0, 3]], method="qgram", q=2)),
            as_num(seq_dist([[1, 2, 3]], [[1, 0, 3]], method="cosine", q=2)),
            as_num(seq_dist([[1, 2, 3]], [[1, 0, 3]], method="jaccard", q=2)),
            round(
                1
                - seq_dist(
                    [utf8_codes("martha")],
                    [utf8_codes("marhta")],
                    method="jw",
                )[0],
                3,
            ),
            as_num(seq_dist([1, 2, 3], [2, 3, 4])),
            as_num(seq_dist([[1, 2, 3]], [[2, 3, 4]])),
            as_num(seq_dist([3.14, 1], [3, 1])),
            as_num(seq_dist([None], [[1, 2]])),
            as_num(seq_dist([[1, None, 3]], [[1, 2, 3]])),
            as_num(seq_dist([[1, 2]], [[1, 2, 3], [4, 5, 6]])),
            as_num(
                seq_dist(
                    [[1, 2, 3]],
                    [[2, 1, 3]],
                    weight=(0.5, 1, 1, 1),
                )
            ),
            cross,
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
