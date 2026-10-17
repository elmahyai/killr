import contextlib
import io
import json
import statistics
import time

from progressr.evaluate import with_progress
from progressr.progressor import progressor
from progressr.reporters import handler_void


def one():
    bare = handler_void()
    out = io.StringIO()
    err = io.StringIO()

    def body():
        progress = progressor(steps=2, on_exit=False)
        progress(message="a")
        progress(message="b")
        return 6

    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        value = with_progress(
            body,
            handlers=handler_void(enable=True),
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    return {
        "enable": bare._env["enable"],
        "target": bare._env["target"],
        "intrusiveness": bare._env["intrusiveness"],
        "result": value,
        "output": out.getvalue() + err.getvalue(),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
