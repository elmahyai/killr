import statistics
import time

from rlang.na_or import Character, Integer, NA, na_or


def one():
    left = na_or(Character(["a", "b", NA, "c"]), "default")
    right = na_or(Integer([1, NA, 3, NA, NA]), Integer([6, 7, 8, 9, 10]))
    return (
        ",".join(str(item) for item in left.values)
        + " "
        + ",".join(str(item) for item in right.values)
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
