import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generics.forecast import (
    MISSING,
    ForecastError,
    Array,
    List,
    Matrix,
    Object,
    forecast,
    force,
    missing,
    next_method,
    register,
    register_s4,
    reset_methods,
    unregister,
)


def floats(obj):
    if isinstance(obj, Object):
        obj = obj.value
    if isinstance(obj, (Matrix, Array)):
        obj = obj.values
    if isinstance(obj, bool):
        return [float(obj)]
    if isinstance(obj, (int, float)):
        return [float(obj)]
    return [float(value) for value in obj]


def err(fn):
    try:
        fn()
        return "OK"
    except ForecastError as exc:
        return exc.message


def one():
    reset_methods()
    register_s4("AccC", ("AccP",))

    def mod(object, *args, w=1):
        del args
        values = [abs(value) for value in floats(object)]
        return sum(values) / len(values) * w

    def sub(object, *args, **kwargs):
        del object, args, kwargs
        return 100

    def sq(object, *args, **kwargs):
        del args, kwargs
        values = floats(object)
        return math.sqrt(sum(value * value for value in values) / len(values))

    def child(object, *args, **kwargs):
        del args, kwargs
        return floats(object)[0] + next_method()

    def parent(object, *args, **kwargs):
        del args, kwargs
        return sum(floats(object))

    def double(object, *args, **kwargs):
        del args, kwargs
        if missing(object):
            return -8
        return sum(floats(object)) + 1

    def integer(object, *args, **kwargs):
        del args, kwargs
        return sum(floats(object)) - 1

    def numeric(object, *args, **kwargs):
        del args, kwargs
        if missing(object):
            return -9
        return sum(floats(object))

    def array(object, *args, **kwargs):
        del args, kwargs
        return sum(floats(object)) + 0.25

    def acc_p(object, *args, **kwargs):
        del args, kwargs
        return object.value * 2

    def default(object, *args, **kwargs):
        del object, args, kwargs
        return -1

    def null(object, *args, **kwargs):
        del args, kwargs
        if missing(object):
            return -2
        return -3

    def name(object, *args, **kwargs):
        del args, kwargs
        if missing(object):
            return -7
        return -6

    def strict(object):
        return object

    def only(object, *args, **kwargs):
        del object, args, kwargs
        return next_method()

    register("mod", mod)
    register("sub", sub)
    register("sq", sq)
    register("child", child)
    register("parent", parent)
    register("double", double)
    register("integer", integer)
    register("numeric", numeric)
    register("array", array)
    register("AccP", acc_p)
    register("default", default)
    register("NULL", null)
    register("name", name)
    register("strict", strict)
    register("only", only)

    series = Object([1, -2, 3.5], ["mod"])
    nums = [
        forecast(series),
        forecast(series, w=2),
        forecast(series, 2),
        forecast(obj=series, w=4),
        forecast(Object([1, -2, 3.5], ["sub", "mod"])),
        forecast(Object([1, -2, 3.5], ["nope", "mod"])),
        forecast(Object([3, 4], ["nope", "sq"])),
        forecast(Object([1.5, 2.5], ["child", "parent"])),
        forecast([1.5, 2.5]),
        forecast([1, 2, 3]),
        forecast(Matrix([1, 2, 3, 4], 2)),
        forecast(Matrix([1.5, 2.5], 1)),
        forecast(Array([1.5, 2.5], (1, 1, 2))),
        forecast(Object(1.25, ["AccC"], s4=True)),
        forecast(Object(9, ["unknown"])),
        forecast(None),
        forecast(),
        forecast(z=1.5),
        forecast(1, object=[1.5, 2.5]),
        forecast(objectt=1.0),
        forecast(obj=[1.5, 2.5]),
        forecast(obj=1, object=[1.5, 2.5]),
        forecast(Object("x", ["name"])),
    ]

    unregister("double", "integer", "array")
    nums.extend(
        [
            forecast([1.5, 2.5]),
            forecast([1, 2, 3]),
            forecast(Matrix([1.5, 2.5], 1)),
            forecast(Array([1.5, 2.5], (1, 1, 2))),
            forecast(z=1.5),
            forecast(object=MISSING, z=1.5),
        ]
    )

    unregister("numeric", "default", "NULL", "AccP", "name")
    errs = [
        err(lambda: forecast([1.5, 2.5])),
        err(lambda: forecast([1, 2, 3])),
        err(lambda: forecast(Matrix([1, 2, 3, 4], 2))),
        err(lambda: forecast(Array([1.5, 2.5], (1, 1, 2)))),
        err(lambda: forecast(True)),
        err(lambda: forecast("ab")),
        err(lambda: forecast(None)),
        err(lambda: forecast()),
        err(lambda: forecast(z=1.5)),
        err(lambda: forecast(z="ab")),
        err(lambda: forecast(Object(1, ["aa", "bb"]))),
        err(lambda: forecast(Object(1, [""]))),
        err(lambda: forecast(Object(1, ["a'b"]))),
        err(lambda: forecast(Object(1, ["a'b", "c"]))),
        err(lambda: forecast(Object(1.0, ["AccC"], s4=True))),
        err(lambda: forecast(List([1]))),
        err(lambda: forecast(1 + 2j)),
        err(lambda: forecast(len)),
        err(lambda: forecast(object=MISSING)),
        err(lambda: forecast(o=1, ob=2)),
        err(lambda: forecast(Object(1, ["strict"]), 2)),
        err(lambda: forecast(Object(1, ["strict"]), 2, z=3)),
        err(lambda: forecast(Object(1, ["strict"]), w=4)),
        err(lambda: forecast(Object(1, ["only", "other"]))),
    ]

    def need(object, *args, **kwargs):
        del args, kwargs
        force(object)

    register("default", need)
    errs.append(err(lambda: forecast()))
    body = ",".join(format(value, ".17g") for value in nums)
    return body + " || " + " || ".join(errs)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")

reset_methods()


def demo(object, *args, **kwargs):
    del args, kwargs
    values = object.value
    return len(values), sum(values)


message = err(lambda: forecast([1, 2, 3]))
register("demo", demo)
count, total = forecast(Object([1, 2, 4], ["demo"]))
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "forecast-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(message + "\n" + f"n {count}\n" + f"total {total}\n")
