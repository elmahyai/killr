import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr")

from httr.date import POSIXct, http_date


def show(value):
    if value is None:
        return "NULL"
    values = getattr(value, "values", None)
    if values is None:
        return "OTHER " + type(value).__name__
    body = " | ".join("NA" if item is None else item for item in values)
    names = getattr(value, "names", None)
    names = "" if not names else ",".join(names)
    return f"chr[{body}] names={names}"


def grab(fn):
    try:
        return show(fn())
    except ValueError as exc:
        return "ERR " + str(exc)


def one():
    lines = [
        show(http_date(POSIXct(784111777))),
        show(http_date(POSIXct(0))),
        show(http_date(POSIXct(-1))),
        show(http_date(POSIXct(-0.1))),
        show(http_date(POSIXct(-1.1))),
        show(http_date(POSIXct(784111777.9))),
        show(http_date(POSIXct(784111777.999999))),
        show(http_date(POSIXct(-86400.2))),
        show(http_date(POSIXct(784129777))),
        show(http_date(POSIXct([None]))),
        show(http_date(POSIXct(float("nan")))),
        show(http_date(POSIXct([float("inf"), float("-inf"), float("nan")]))),
        show(http_date(POSIXct([None, float("nan")]))),
        show(http_date(POSIXct([]))),
        show(http_date(None)),
        show(http_date(POSIXct([0, None], names=["a", "b"]))),
        grab(lambda: http_date("Sun, 06 Nov 1994 08:49:37 GMT")),
        grab(lambda: http_date(1)),
        grab(lambda: http_date("1994-11-06")),
    ]
    return "\n".join(lines)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
