import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generics.intersect import (
    MISSING,
    Array,
    IntersectError,
    List,
    Matrix,
    Object,
    intersect,
    combine_errs,
    duplicate_x_error,
    duplicate_y_error,
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
        return fn()
    except IntersectError as exc:
        return exc.message


def one():
    reset_methods()
    register_s4("AccC", ("AccP",))

    def mod(x, y, *args, w=1):
        del y, args
        values = [abs(value) for value in floats(x)]
        return sum(values) / len(values) * w

    def sub(x, y, *args, **kwargs):
        del y, x, args, kwargs
        return 100

    def sq(x, y, *args, **kwargs):
        del y, args, kwargs
        values = floats(x)
        return math.sqrt(sum(value * value for value in values) / len(values))

    def child(x, y, *args, **kwargs):
        del y, args, kwargs
        return floats(x)[0] + next_method()

    def parent(x, y, *args, **kwargs):
        del y, args, kwargs
        return sum(floats(x))

    def double(x, y, *args, **kwargs):
        del y, args, kwargs
        if missing(x):
            return -8
        return sum(floats(x)) + 1

    def integer(x, y, *args, **kwargs):
        del y, args, kwargs
        return sum(floats(x)) - 1

    def numeric(x, y, *args, **kwargs):
        del y, args, kwargs
        if missing(x):
            return -9
        return sum(floats(x))

    def array(x, y, *args, **kwargs):
        del y, args, kwargs
        return sum(floats(x)) + 0.25

    def acc_p(x, y, *args, **kwargs):
        del y, args, kwargs
        return x.value * 2

    def default(x, y, *args, **kwargs):
        del y, x, args, kwargs
        return -1

    def null(x, y, *args, **kwargs):
        del y, args, kwargs
        if missing(x):
            return -2
        return -3

    def name(x, y, *args, **kwargs):
        del y, args, kwargs
        if missing(x):
            return -7
        return -6

    def strict(x):
        return x

    def only(x, y, *args, **kwargs):
        del y, x, args, kwargs
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
        intersect(series),
        intersect(series, w=2),
        intersect(series, 2),
        intersect(x=series, w=4),
        intersect(Object([1, -2, 3.5], ["sub", "mod"])),
        intersect(Object([1, -2, 3.5], ["nope", "mod"])),
        intersect(Object([3, 4], ["nope", "sq"])),
        intersect(Object([1.5, 2.5], ["child", "parent"])),
        intersect([1.5, 2.5]),
        intersect([1, 2, 3]),
        intersect(Matrix([1, 2, 3, 4], 2)),
        intersect(Matrix([1.5, 2.5], 1)),
        intersect(Array([1.5, 2.5], (1, 1, 2))),
        intersect(Object(1.25, ["AccC"], s4=True)),
        intersect(Object(9, ["unknown"])),
        intersect(None),
        intersect(),
        intersect(z=1.5),
        intersect(1, x=[1.5, 2.5]),
        intersect(xx=1.0),
        intersect(x=[1.5, 2.5]),
        intersect(Object("x", ["name"])),
    ]

    unregister("double", "integer", "array")
    nums.extend(
        [
            intersect([1.5, 2.5]),
            intersect([1, 2, 3]),
            intersect(Matrix([1.5, 2.5], 1)),
            intersect(Array([1.5, 2.5], (1, 1, 2))),
            intersect(z=1.5),
            intersect(x=MISSING, z=1.5),
        ]
    )

    unregister("numeric", "default", "NULL", "AccP", "name")
    errs = [
        err(lambda: intersect([1.5, 2.5], 0)),
        err(lambda: intersect([1, 2, 3], 0)),
        err(lambda: intersect(Matrix([1, 2, 3, 4], 2), 0)),
        err(lambda: intersect(Array([1.5, 2.5], (1, 1, 2)), 0)),
        err(lambda: intersect(True, 0)),
        err(lambda: intersect("ab", 0)),
        err(lambda: intersect(None, 0)),
        err(lambda: intersect()),
        err(lambda: intersect(z=1.5)),
        err(lambda: intersect(z="ab")),
        err(lambda: intersect(Object(1, ["aa", "bb"]), 0)),
        err(lambda: intersect(Object(1, [""]), 0)),
        err(lambda: intersect(Object(1, ["a'b"]), 0)),
        err(lambda: intersect(Object(1, ["a'b", "c"]), 0)),
        err(lambda: intersect(Object(1.0, ["AccC"], s4=True), 0)),
        err(lambda: intersect(List([1]), 0)),
        err(lambda: intersect(1 + 2j, 0)),
        err(lambda: intersect(len, 0)),
        err(lambda: intersect(x=MISSING, y=0)),
        err(duplicate_x_error),
        err(duplicate_y_error),
        err(lambda: intersect(Object(1, ["strict"]), 2)),
        err(lambda: intersect(Object(1, ["strict"]), 2, z=3)),
        err(lambda: intersect(Object(1, ["strict"]), w=4)),
        err(lambda: intersect(Object(1, ["only", "other"]), 0)),
    ]

    def need(x, y, *args, **kwargs):
        del y, args, kwargs
        force(x)

    register("default", need)
    errs.append(err(lambda: intersect()))
    body = ",".join(format(value, ".17g") for value in nums)
    return body + " || " + combine_errs(errs)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")

reset_methods()


def demo(x, y, *args, **kwargs):
    del y, args, kwargs
    values = x.value
    return len(values), sum(values)


message = err(lambda: intersect([1, 2, 3]))
register("demo", demo)
count, total = intersect(Object([1, 2, 4], ["demo"]))
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "intersect-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
prefix = str(message)
out.write_text(prefix + "\n" + f"n {count}\n" + f"total {total}\n")
