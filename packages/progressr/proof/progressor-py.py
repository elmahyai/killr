import json
import statistics
import time

from progressr.condition import condition_message
from progressr.evaluate import with_progress
from progressr.factory import make_progression_handler
from progressr.progressor import progressor


def one():
    seen = []

    def update(config, state, progression, **_kwargs):
        seen.append(
            {
                "type": progression["type"],
                "amount": progression["amount"],
                "message": condition_message(progression),
            }
        )

    handler = make_progression_handler(
        "rec",
        reporter={"update": update},
        enable=True,
        target="file",
        interval=0,
    )
    box = {}

    def body():
        progress = progressor(steps=4)
        box["length"] = len(progress)
        for text in ("one", "two", "three", "four"):
            progress(message=text)

    with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    return {"length": box["length"], "events": seen}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
