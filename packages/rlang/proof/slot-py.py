import statistics
import time

from rlang.slot import WithAttrs, slot


def one():
    x = WithAttrs(None, {"test": 42, "tag": "x"})
    missing = slot(x, "nope")
    return " ".join(
        [
            str(slot(x, "test")),
            str(slot(x, "tag")),
            "NULL" if missing is None else "notnull",
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
