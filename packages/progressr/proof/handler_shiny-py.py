import json
import statistics
import time

from progressr.evaluate import with_progress
from progressr.external import handler_shiny
from progressr.options import ProgressrError
from progressr.progressor import progressor


def one():
    def body():
        progress = progressor(steps=2, on_exit=False)
        progress()
        progress()
    try:
        with_progress(body, handlers=handler_shiny(enable=True), enable=True, interval=0, delay_terminal=False, delay_stdout=False, delay_conditions=())
    except ProgressrError as exc:
        return str(exc)
    raise AssertionError("handler_shiny() did not error")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"message": value, "median_ms": statistics.median(elapsed)}))
