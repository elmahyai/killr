import json
import statistics
import time

from progressr.condition import with_calling_handlers
from progressr.evaluate import without_progress
from progressr.factory import make_progression_handler
from progressr.progressor import progressor


def one():
    seen = []
    handler = make_progression_handler(
        "rec",
        reporter={
            "initiate": lambda **_kwargs: seen.append("i"),
            "update": lambda **_kwargs: seen.append("u"),
        },
        enable=True,
        target="file",
        interval=0,
    )

    def body():
        progress = progressor(along=range(1, 6))
        total = 0
        for value in range(1, 6):
            total += value
            progress(message=str(value))
        return total

    def wrapped():
        return without_progress(body)

    total = with_calling_handlers(wrapped, progression=handler)
    return {"sum": total, "seen": len(seen)}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
