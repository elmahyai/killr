import contextlib
import io
import json
import statistics
import time

from magrittr.pipe import DOT, pipe_eager_lexical


def fsub(a, b):
    return a - b


def one():
    return [
        pipe_eager_lexical(list(range(1, 11)), sum),
        pipe_eager_lexical(10, (fsub, (3,), {})),
        pipe_eager_lexical(10, (fsub, (3, DOT), {})),
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


sentence = "pipe_eager_lexical(1:10, sum) returns 55.\n"
path = "/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/pipe_eager_lexical-python.txt"
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
    pipe_eager_lexical(None, foo, bar, baz)
messages = buffer.getvalue().splitlines()
print(json.dumps({"value": value, "messages": messages, "median_ms": statistics.median(elapsed)}))
