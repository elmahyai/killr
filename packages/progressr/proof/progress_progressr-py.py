import json
import statistics
import time

from progressr.evaluate import with_progress
from progressr.external import progress_progressr
from progressr.factory import make_progression_handler


def one():
    events = []

    def push(config, state, progression, **kwargs):
        events.append((progression["type"], progression["amount"]))

    handler = make_progression_handler(
        "record",
        reporter={"initiate": push, "update": push, "finish": push},
        enable=True,
        intrusiveness=1,
        interval=0,
    )

    def body():
        bar = progress_progressr()
        bar["init"](3)
        bar["step"]()
        bar["step"]()
        bar["term"]()
        return 3

    result = with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    return {
        "result": result,
        "types": [item[0] for item in events],
        "amounts": [item[1] for item in events],
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
