import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmap.fastmap import fastmap

root = Path(__file__).resolve().parent
package = root.parent


def codes(keys):
    if not keys:
        return []
    return [float(ord(ch)) for ch in "\n".join(keys)]


def one():
    m = fastmap()
    m.set("a", 1.5)
    m.set("b", 2.25)
    m.set("v", [1.5, 2.25, 3.125])
    m.set("z", 9)
    m.set("é", 8)
    m.set("none", None)
    for i in range(1, 41):
        m.set(f"k{i:02d}", i + 0.5)
    out = [
        float(m.size()),
        float(m.get("a")),
        float(m.get("b")),
        float(m.get("z")),
        float(m.get("é")),
        *[float(v) for v in m.get("v")],
        1.0 if m.has("none") else 0.0,
        1.0 if m.get("none") is None else 0.0,
        1.0 if m.has("missing") else 0.0,
        1.0 if m.get("missing") is None else 0.0,
        *codes(m.keys()),
        *codes(m.keys(sort=True)),
    ]
    removed = m.remove(["b", "k02", "b", "missing"])
    for i in range(1, 41, 2):
        m.remove(f"k{i:02d}")
    m2 = m.clone()
    m2.set("a", 99.5)
    m.set("z", 7.5)
    err1 = _err(lambda: m.set(1, 1))
    err2 = _err(lambda: m.set("", 1))
    got = m.mget(["a", "é", "k04"])
    out.extend(1.0 if flag else 0.0 for flag in removed)
    out.append(float(m.size()))
    out.extend(codes(m.keys()))
    out.extend(codes(m.keys(sort=True)))
    out.extend(
        [
            float(m.get("a")),
            float(m2.get("a")),
            float(m.get("z")),
            float(m2.get("z")),
            *[float(v) for v in got],
            float(len(err1)),
            *[float(ord(ch)) for ch in err1],
            float(len(err2)),
            *[float(ord(ch)) for ch in err2],
        ]
    )
    return out


def _err(fn):
    try:
        fn()
    except ValueError as exc:
        return str(exc)
    return ""


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "fastmap-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)

def word(flag):
    return "TRUE" if flag else "FALSE"


m = fastmap()
m.set("x", 100)
m.set("letters", ["a", "b", "c"])
m.mset(numbers=[10, 20, 30])
example = (
    f"get x {m.get('x')}\n"
    f"get numbers {' '.join(str(v) for v in m.get('numbers'))}\n"
    f"keys {' '.join(m.keys(sort=True))}\n"
    f"size {m.size()}\n"
    f"remove x {word(m.remove('x'))}\n"
    f"size {m.size()}\n"
    f"missing {word(m.get('x') is None)}\n"
)
(package / "docs" / "output" / "fastmap-python.txt").write_text(example)
