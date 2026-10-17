import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmap.fastqueue import fastqueue

root = Path(__file__).resolve().parent
package = root.parent


def one():
    q = fastqueue(3)
    for i in range(1, 13):
        q.add(i + 0.5)
    first = list(q.as_list())
    removed = [q.remove() for _ in range(4)]
    q.madd(13.5, 14.5, _list=[15.5, 16.5])
    second = list(q.as_list())
    third = list(q.mremove(3))
    size1 = q.size()
    peek1 = q.peek()
    while q.size() > 0:
        q.remove()
    empty = 1.0 if q.remove() is None else 0.0
    q.add(None)
    null_kept = 1.0 if q.remove(missing=-1) is None else 0.0
    empty2 = q.remove(missing=-1)
    q.reset()
    q.add(1.25)

    q2 = fastqueue(3)
    q2.madd(1, 2, _list=[3])
    order1 = list(q2.as_list())
    q2.madd(4, 5, 6, 7)
    q2.madd(8, 9)
    for _ in range(5):
        q2.remove()
    q2.madd(10, 11, 12, 13, 14, 15, 16)
    wrap = list(q2.as_list())

    q3 = fastqueue(3)
    q3.madd(1, 2, 3, 4, 5, 6)
    six = list(q3.as_list())
    onev = q3.remove()
    q3.madd(7, 8, 9, 10, 11, 12, 13, 14)
    grown = list(q3.as_list())
    for _ in range(6):
        q3.remove()
    mid = list(q3.as_list())
    shr = q3.remove()
    after = list(q3.as_list())
    values = [
        *first,
        *removed,
        *second,
        *third,
        size1,
        peek1,
        empty,
        null_kept,
        empty2,
        q.size(),
        q.peek(),
        *order1,
        *wrap,
        *six,
        onev,
        *grown,
        *mid,
        shr,
        *after,
    ]
    return [float(v) for v in values]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "fastqueue-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)

q = fastqueue(3)
q.add(1)
q.add(2)
q.add(3)
q.add(4)
example = (
    f"as_list {' '.join(str(v) for v in q.as_list())}\n"
    f"remove {q.remove()}\n"
    f"size {q.size()}\n"
    f"peek {q.peek()}\n"
)
(package / "docs" / "output" / "fastqueue-python.txt").write_text(example)
