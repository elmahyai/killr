import contextlib
import io
import json
import statistics
import time

from cli import options as cli_options
from progressr.cli_handlers import handler_pbcol
from progressr.evaluate import with_progress
from progressr.progressor import progressor

cli_options(**{"width": 80})


def one():
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        handler = handler_pbcol(clear=False, enable=True)

        def body():
            progress = progressor(steps=4, on_exit=False)
            for index in range(1, 5):
                progress(message=f"m{index}")

        with_progress(
            body,
            handlers=handler,
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    return {"err": buf.getvalue(), "clear": handler._env["clear"], "target": handler._env["target"]}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
