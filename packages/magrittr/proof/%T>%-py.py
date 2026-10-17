import contextlib
import io
import json
import statistics
import time

from magrittr.pipe import tee


def one():
    return list(tee(list(range(1, 11)), sum))


def foo(value):
    print("foo")
    return value


def bar(value):
    print("bar")
    return value


def baz(value):
    print("baz")
    return value


sentence = "1:10 %T>% sum returns 1:10.\n"
path = "/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/%T>%-python.txt"
with open(path, "w", encoding="utf-8") as handle:
    handle.write(sentence)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    tee(None, foo, bar, baz)
messages = buffer.getvalue().splitlines()
print(json.dumps({"value": value, "messages": messages, "median_ms": statistics.median(elapsed)}))
