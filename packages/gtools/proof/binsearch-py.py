import json
import statistics
import string
import sys
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.binsearch import binsearch


def flat_result(result):
    where = result["where"]
    value = result["value"]
    if hasattr(where, "__len__") and not isinstance(where, (str, bytes)):
        where_part = [float(x) for x in where]
    else:
        where_part = [float(where)]
    if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        value_part = [float(x) for x in value]
    else:
        value_part = [float(value)]
    return [float(result["numiter"]), *where_part, *value_part]


def one():
    letters = string.ascii_uppercase

    def fun(x):
        index = int(x)
        letter = letters[index - 1]
        if letter > "M":
            return 1.0
        if letter < "M":
            return -1.0
        return 0.0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (
            flat_result(binsearch(lambda x: x - 10, [0, 20]))
            + flat_result(binsearch(lambda x: x - 10.1, [0, 20]))
            + flat_result(binsearch(fun, list(range(1, 27))))
            + flat_result(binsearch(lambda x: x - 25, [0, 20]))
        )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
