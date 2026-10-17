import contextlib
import io
import json
import statistics
import time

from magrittr.pipe import DOT, pipe


def fsub(a, b):
    return a - b


def one():
    return [
        pipe(list(range(1, 11)), sum),
        pipe(10, (fsub, (3,), {})),
        pipe(10, (fsub, (3, DOT), {})),
    ]


def foo(value):
    print("foo")
    return value


def bar(value):
    print("bar")
    return value


def baz(value):
    print("baz")
    return value


sentence = "1:10 %>% sum returns 55.\n"
path = "/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/%>%-python.txt"
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
    pipe(None, foo, bar, baz)
messages = buffer.getvalue().splitlines()
print(json.dumps({"value": value, "messages": messages, "median_ms": statistics.median(elapsed)}))
