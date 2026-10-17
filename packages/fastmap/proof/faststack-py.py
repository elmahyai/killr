import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmap.faststack import faststack
from fastmap.is_key_missing import is_key_missing
from fastmap.key_missing import key_missing

root = Path(__file__).resolve().parent
package = root.parent


def one():
    s = faststack(4)
    s.push(1.5)
    s.push(2.5)
    s.push(3.5)
    s.mpush(4.5, 5.5, _list=[6.5])
    size1 = s.size()
    listed = list(s.as_list())
    top = s.peek()
    p1 = s.pop()
    p2 = s.pop()
    multi = list(s.mpop(3))
    left = list(s.as_list())
    size2 = s.size()
    for i in range(1, 31):
        s.push(i + 0.25)
    size3 = s.size()
    popped = [s.pop() for _ in range(10)]
    rest_size = s.size()
    rest_top = s.peek()
    s.reset()
    empty = s.pop(missing=-999)
    km = faststack(missing_default=key_missing())
    flag = 1.0 if is_key_missing(km.pop()) else 0.0
    flag2 = 1.0 if is_key_missing(km.peek()) else 0.0
    values = [
        size1,
        *listed,
        top,
        p1,
        p2,
        *multi,
        *left,
        size2,
        size3,
        *popped,
        rest_size,
        rest_top,
        empty,
        flag,
        flag2,
        s.size(),
    ]
    return [float(v) for v in values]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "faststack-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)

s = faststack()
s.push(5)
s.push(6)
s.push(7)
example = (
    f"size {s.size()}\n"
    f"as_list {' '.join(str(v) for v in s.as_list())}\n"
    f"pop {s.pop()}\n"
    f"peek {s.peek()}\n"
    f"size {s.size()}\n"
)
(package / "docs" / "output" / "faststack-python.txt").write_text(example)
