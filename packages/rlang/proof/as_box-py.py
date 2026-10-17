import statistics
import time

from rlang.as_box import as_box, is_box, new_box, unbox


def one():
    boxed = new_box(list("abcdefghijklmnopqrstuvwxyz"), "mybox")
    boxed2 = as_box(boxed, "mybox")
    fresh = as_box(42, "numbox")
    return "|".join(
        [
            "TRUE" if boxed2 is boxed else "FALSE",
            str(unbox(fresh)),
            "TRUE" if is_box(fresh, "numbox") else "FALSE",
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
