import statistics
import time

from rlang.slot import S4, WithAttrs, slot, slot_replace


def one():
    x = WithAttrs(None, {"test": 42, "tag": "x"})
    slot_replace(x, "test", 99)
    slot_replace(x, "new", "added")
    slot_replace(x, "tag", None)
    fievel = S4("Person", name="Fievel", species="mouse")
    slot_replace(fievel, "name", "Updated")
    slot_replace(fievel, "species", "rat")
    return " ".join(
        [
            str(slot(x, "test")),
            "NULL" if slot(x, "new") is None else str(slot(x, "new")),
            "NULL" if slot(x, "tag") is None else "notnull",
            str(slot(fievel, "name")),
            str(slot(fievel, "species")),
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
