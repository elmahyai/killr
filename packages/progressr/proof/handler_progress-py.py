import contextlib
import io
import json
import statistics
import time

from progressr.backends import handler_progress
from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor


def one():
    try:
        handler_progress(type="nope")
        bad = ""
    except ProgressrError as exc:
        bad = str(exc)
    buf = io.StringIO()

    def body():
        progress = progressor(steps=4, on_exit=False)
        for index in range(1, 5):
            progress(message=f"m{index}")

    with contextlib.redirect_stderr(buf):
        with_progress(
            body,
            handlers=handler_progress(
                format=":spin [:bar] :percent :message",
                width=40,
                clear=False,
                enable=True,
            ),
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    err = buf.getvalue()
    return {"bad_type": bad, "err": err, "nchar": len(err)}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
