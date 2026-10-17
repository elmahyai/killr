import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmap.fastmap import fastmap
from fastmap.fastqueue import fastqueue
from fastmap.faststack import faststack
from fastmap.is_key_missing import is_key_missing
from fastmap.key_missing import key_missing

root = Path(__file__).resolve().parent
package = root.parent

km = key_missing()
plain = fastmap()
sentinel = fastmap(missing_default=km)


def flag(value):
    return 1.0 if is_key_missing(value) else 0.0


def one():
    return [
        flag(km),
        flag(None),
        flag(1),
        flag([]),
        flag("key_missing"),
        flag(sentinel.get("absent")),
        flag(plain.get("absent")),
        flag(fastqueue().remove()),
        flag(faststack(missing_default=km).pop()),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "is.key_missing-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)

def word(flag):
    return "TRUE" if flag else "FALSE"


example = (
    f"sentinel {word(is_key_missing(km))}\n"
    f"null {word(is_key_missing(None))}\n"
    f"number {word(is_key_missing(1))}\n"
    f"list {word(is_key_missing([]))}\n"
    f"map {word(is_key_missing(sentinel.get('absent')))}\n"
    f"plain {word(is_key_missing(plain.get('absent')))}\n"
    f"stack {word(is_key_missing(faststack(missing_default=km).pop()))}\n"
)
(package / "docs" / "output" / "is.key_missing-python.txt").write_text(example)
