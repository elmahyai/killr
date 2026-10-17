import json
import statistics
import time

from progressr.factory import make_progression_handler
from progressr.handlers import handlers
from progressr.options import set_option


def one():
    set_option("progressr.handlers", None)
    handler = make_progression_handler(
        "rec",
        reporter={"update": lambda config, state, progression, **_kwargs: None},
        enable=True,
        target="file",
        interval=0,
    )
    second = make_progression_handler("other", enable=True, target="file")
    handlers(rec=handler)
    current = handlers()
    previous = handlers(extra=second, append=True)
    return {
        "read_back": len(current),
        "name": current._names[0],
        "previous": len(previous),
        "after": len(handlers()),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
