import json
import os
import statistics
import tempfile
import time

from progressr.bars import handler_txtprogressbar
from progressr.evaluate import with_progress
from progressr.progressor import progressor


def _fresh(name):
    return os.path.join(tempfile.mkdtemp(), name)


def bar_text(style):
    path = _fresh("txt.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")
    handler = handler_txtprogressbar(style=style, file=handle, enable=True, clear=False)

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="one")
        progress(message="two")
        progress(message="three")
        progress(message="four")

    with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    handle.close()
    return open(path, "rb").read().decode("utf-8")


def one():
    return {"style3": bar_text(3), "style1": bar_text(1)}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
