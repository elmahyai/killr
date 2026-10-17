import json
import statistics
import time

from progressr.evaluate import with_progress
from progressr.progressor import progressor
from progressr.reporters import handler_slowdown


def one():
    handler = handler_slowdown(duration=0, enable=True)

    def body():
        progress = progressor(steps=20, on_exit=False)
        total = 0
        for i in range(1, 21):
            progress(message="s")
            total += i
        return total

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
        "intrusiveness": handler._env["intrusiveness"],
        "target": handler._env["target"],
        "result": result,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
