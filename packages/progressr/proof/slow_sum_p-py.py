import json
import statistics
import time

from progressr.condition import condition_message, try_invoke_restart, with_calling_handlers
from progressr.demo import slow_sum_p
from progressr.evaluate import with_progress
from progressr.factory import make_progression_handler
from progressr.options import set_option

set_option("progressr.enable", True)


def one():
    lines = []

    def update(config, state, progression, **_kwargs):
        text = condition_message(progression).replace("\n", "")
        if text:
            lines.append(text)

    handler = make_progression_handler(
        "rec",
        reporter={"update": update},
        enable=True,
        target="file",
        interval=0,
    )

    def on_message(condition):
        lines.append(condition_message(condition).replace("\n", ""))
        try_invoke_restart("muffleMessage", condition)

    def body():
        return slow_sum_p(
            list(range(1, 4)),
            delay=0,
            stdout=False,
            message=True,
            sticky=False,
            progress=True,
        )

    def run():
        return with_progress(
            body,
            handlers=handler,
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )

    value = with_calling_handlers(run, message=on_message)
    storage = "integer" if type(value) is int else "double"
    return {"value": value, "storage": storage, "lines": lines}


ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
ans["median_ms"] = statistics.median(elapsed)
print(json.dumps(ans))
