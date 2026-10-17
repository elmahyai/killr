import json
import statistics
import time

from progressr.cli_handlers import handler_tutorial
from progressr.options import ProgressrError


def one():
    handler = handler_tutorial(spec="cli", enable=True)
    prefixed = handler_tutorial(spec="c", enable=True)
    try:
        handler_tutorial(spec="invalid")
        bad = ""
    except ProgressrError as exc:
        bad = str(exc)
    return {
        "class": handler.classes[0],
        "clear": handler._env["clear"],
        "target": handler._env["target"],
        "prefix": prefixed.classes[0],
        "bad_spec": bad,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
