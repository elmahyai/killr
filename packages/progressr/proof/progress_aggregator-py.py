import json
import statistics
import time

from progressr.aggregator import progress_aggregator
from progressr.evaluate import with_progress
from progressr.factory import make_progression_handler
from progressr.options import set_option
from progressr.progressor import progressor

set_option("progressr.enable", True)


def one():
    amounts = []

    def update(config, state, progression, **_kwargs):
        child = progression.get("child")
        if child is not None:
            amounts.append(child["amount"])

    handler = make_progression_handler(
        "rec",
        reporter={"update": update},
        enable=True,
        target="file",
        interval=0,
    )

    def body():
        progress = progressor(steps=2, initiate=True)
        relay = progress_aggregator(progress)

        def child():
            step = progressor(steps=2)
            step(amount=1)
            step(amount=1)
            return 2

        return relay(child)

    value = with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    return {"value": value, "child_amounts": amounts}


ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
ans["median_ms"] = statistics.median(elapsed)
print(json.dumps(ans))
