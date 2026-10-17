import json
import os
import statistics
import tempfile
import time

from progressr.evaluate import with_progress
from progressr.progressor import progressor
from progressr.reporters import handler_ascii_alert


def _fresh(name):
    return os.path.join(tempfile.mkdtemp(), name)


def one():
    bare = handler_ascii_alert()
    path = _fresh("alert.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="a")
        progress(amount=0, message="zero")
        progress(message="ding", amount=0, type="interrupt", class_="control_progression")
        progress(message="b")
        progress(message="c")
        progress(message="d")

    with_progress(
        body,
        handlers=handler_ascii_alert(file=handle, enable=True, intrusiveness=1),
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    handle.close()
    return {
        "intrusiveness": bare._env["intrusiveness"],
        "target": list(bare._env["target"]),
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
