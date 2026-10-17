import json
import os
import statistics
import tempfile
import time

from progressr.evaluate import with_progress
from progressr.progressor import progressor
from progressr.reporters import handler_newline


def _fresh(name):
    return os.path.join(tempfile.mkdtemp(), name)


def one():
    bare = handler_newline()
    path = _fresh("newline.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=3, on_exit=False)
        progress(message="a")
        progress(amount=0, message="still")
        progress(type="hide", class_="control_progression", amount=0)
        progress(type="unhide", class_="control_progression", amount=0)
        progress(message="halted", amount=0, type="interrupt", class_="control_progression")
        progress(message="b")
        progress(message="c")

    with_progress(
        body,
        handlers=handler_newline(file=handle, enable=True),
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    handle.close()
    return {
        "intrusiveness": bare._env["intrusiveness"],
        "target": bare._env["target"],
        "text": open(path, encoding="utf-8").read(),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
