import json
import statistics
import time

from progressr.backends import handler_tkprogressbar
from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor


def _open_bar(handler):
    finish = handler._env["reporter"]["initiate"]
    closed = dict(
        zip(finish.__code__.co_freevars, (cell.cell_contents for cell in finish.__closure__))
    )
    box = closed["pb_config"]
    if box[0] is None:
        return None
    return box[0]["pb"]


def state(steps, clear):
    handler = handler_tkprogressbar(clear=clear, enable=True)

    def body():
        progress = progressor(steps=4, on_exit=False)
        for index in range(1, steps + 1):
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
    pb = _open_bar(handler)
    if pb is None:
        return {"gone": True}
    try:
        snap = pb.snapshot()
    finally:
        pb.kill()
    return {
        "gone": False,
        "title": snap["title"],
        "label": snap["label"],
        "percent": snap["percent"],
        "geometry": snap["geometry"],
    }


def one():
    try:
        handler_tkprogressbar(inputs="x", enable=True)
        bad = ""
    except ProgressrError as exc:
        bad = str(exc)
    return {
        "bad_inputs": bad,
        "none": state(0, False),
        "one": state(1, False),
        "four": state(4, False),
        "cleared": state(4, True),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
