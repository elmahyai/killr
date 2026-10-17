import statistics
import time

from lifecycle import pkg_lifecycle_statuses


def _show(rows):
    if not rows:
        return "EMPTY"
    return ",".join(f"{row['fun']}={row['lifecycle']}" for row in rows)


def one():
    return " || ".join(
        [
            _show(pkg_lifecycle_statuses("lifecycle")),
            _show(pkg_lifecycle_statuses("lifecycle", which=["deprecated", None])),
            _show(pkg_lifecycle_statuses("lifecycle", which="questioning")),
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
