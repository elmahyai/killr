import json
import os
import statistics
import tempfile
import time

from progressr.evaluate import with_progress
from progressr.progressor import progressor
from progressr.reporters import handler_filesize


def _fresh(name):
    return os.path.join(tempfile.mkdtemp(), name)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _run(handler, fn):
    return with_progress(
        fn,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )


def one():
    bare = handler_filesize(file=_fresh("default.progress"))
    path = _fresh("run.progress")
    box = {}

    def body():
        progress = progressor(steps=4, on_exit=False)
        box["init"] = os.path.getsize(path)
        progress(message="work")
        box["first"] = _read(path)
        progress(amount=0, message="hold")
        box["zero"] = _read(path)
        progress(message="broke", amount=1, type="interrupt", class_="control_progression")
        box["interrupt"] = _read(path)
        progress(message="go")
        progress(message="go")
        progress(message="go")

    _run(handler_filesize(file=path, enable=True, clear=False, intrusiveness=0), body)
    cleared = _fresh("clear.progress")

    def clear_body():
        progress = progressor(steps=2, on_exit=False)
        progress(message="x")
        progress(message="y")

    _run(handler_filesize(file=cleared, enable=True, clear=True, intrusiveness=0), clear_body)
    zero = _fresh("zero.progress")

    def zero_body():
        progressor(steps=0, on_exit=False)

    _run(handler_filesize(file=zero, enable=True, clear=False, intrusiveness=0), zero_body)
    missing = _fresh("off.progress")

    def off_body():
        progress = progressor(steps=2, on_exit=False)
        progress(message="x")
        progress(message="y")

    _run(handler_filesize(file=missing, enable=False), off_body)
    return {
        "intrusiveness": bare._env["intrusiveness"],
        "target": bare._env["target"],
        "init": box["init"],
        "first": box["first"],
        "zero": box["zero"],
        "interrupt": box["interrupt"],
        "final": _read(path),
        "final_size": os.path.getsize(path),
        "cleared": os.path.exists(cleared),
        "zero_steps": _read(zero),
        "zero_size": os.path.getsize(zero),
        "disabled": os.path.exists(missing),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
