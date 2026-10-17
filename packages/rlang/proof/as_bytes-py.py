import statistics
import time

from rlang.as_bytes import as_bytes


def fmt(v):
    return f"{float(v):.17g}"


def one():
    num = as_bytes([1000, 2500000])
    chr_ = as_bytes(["1MB", "500KB", "1K"])
    total = as_bytes(["1MB", "5MB", "500KB"])
    return "|".join(
        [
            ",".join(fmt(v) for v in num.unclass()),
            ",".join(fmt(v) for v in chr_.unclass()),
            fmt(float(total.unclass().sum())),
            "TRUE" if as_bytes(num) is num else "FALSE",
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
