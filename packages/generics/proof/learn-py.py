import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generics.learn import (
    MISSING,
    Array,
    LearnError,
    List,
    Matrix,
    Object,
    learn,
    combine_errs,
    duplicate_x_error,
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
    except LearnError as exc:
        return exc.message


def one():
    reset_methods()
    register_s4("AccC", ("AccP",))

    def mod(x, *args, w=1):
        del args
        values = [abs(value) for value in floats(x)]
        return sum(values) / len(values) * w

    def sub(x, *args, **kwargs):
        del x, args, kwargs
        return 100

    def sq(x, *args, **kwargs):
        del args, kwargs
        values = floats(x)
        return math.sqrt(sum(value * value for value in values) / len(values))

    def child(x, *args, **kwargs):
        del args, kwargs
        return floats(x)[0] + next_method()

    def parent(x, *args, **kwargs):
        del args, kwargs
        return sum(floats(x))

    def double(x, *args, **kwargs):
        del args, kwargs
        if missing(x):
            return -8
        return sum(floats(x)) + 1

    def integer(x, *args, **kwargs):
        del args, kwargs
        return sum(floats(x)) - 1

    def numeric(x, *args, **kwargs):
        del args, kwargs
        if missing(x):
            return -9
        return sum(floats(x))

    def array(x, *args, **kwargs):
        del args, kwargs
        return sum(floats(x)) + 0.25

    def acc_p(x, *args, **kwargs):
        del args, kwargs
        return x.value * 2

    def default(x, *args, **kwargs):
        del x, args, kwargs
        return -1

    def null(x, *args, **kwargs):
        del args, kwargs
        if missing(x):
            return -2
        return -3

    def name(x, *args, **kwargs):
        del args, kwargs
        if missing(x):
            return -7
        return -6

    def strict(x):
        return x

    def only(x, *args, **kwargs):
        del x, args, kwargs
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
        learn(series),
        learn(series, w=2),
        learn(series, 2),
        learn(x=series, w=4),
        learn(Object([1, -2, 3.5], ["sub", "mod"])),
        learn(Object([1, -2, 3.5], ["nope", "mod"])),
        learn(Object([3, 4], ["nope", "sq"])),
        learn(Object([1.5, 2.5], ["child", "parent"])),
        learn([1.5, 2.5]),
        learn([1, 2, 3]),
        learn(Matrix([1, 2, 3, 4], 2)),
        learn(Matrix([1.5, 2.5], 1)),
        learn(Array([1.5, 2.5], (1, 1, 2))),
        learn(Object(1.25, ["AccC"], s4=True)),
        learn(Object(9, ["unknown"])),
        learn(None),
        learn(),
        learn(z=1.5),
        learn(1, x=[1.5, 2.5]),
        learn(xx=1.0),
        learn(x=[1.5, 2.5]),
        learn(Object("x", ["name"])),
    ]

    unregister("double", "integer", "array")
    nums.extend(
        [
            learn([1.5, 2.5]),
            learn([1, 2, 3]),
            learn(Matrix([1.5, 2.5], 1)),
            learn(Array([1.5, 2.5], (1, 1, 2))),
            learn(z=1.5),
            learn(x=MISSING, z=1.5),
        ]
    )

    unregister("numeric", "default", "NULL", "AccP", "name")
    errs = [
        err(lambda: learn([1.5, 2.5])),
        err(lambda: learn([1, 2, 3])),
        err(lambda: learn(Matrix([1, 2, 3, 4], 2))),
        err(lambda: learn(Array([1.5, 2.5], (1, 1, 2)))),
        err(lambda: learn(True)),
        err(lambda: learn("ab")),
        err(lambda: learn(None)),
        err(lambda: learn()),
        err(lambda: learn(z=1.5)),
        err(lambda: learn(z="ab")),
        err(lambda: learn(Object(1, ["aa", "bb"]))),
        err(lambda: learn(Object(1, [""]))),
        err(lambda: learn(Object(1, ["a'b"]))),
        err(lambda: learn(Object(1, ["a'b", "c"]))),
        err(lambda: learn(Object(1.0, ["AccC"], s4=True))),
        err(lambda: learn(List([1]))),
        err(lambda: learn(1 + 2j)),
        err(lambda: learn(len)),
        err(lambda: learn(x=MISSING)),
        err(duplicate_x_error),
        err(lambda: learn(Object(1, ["strict"]), 2)),
        err(lambda: learn(Object(1, ["strict"]), 2, z=3)),
        err(lambda: learn(Object(1, ["strict"]), w=4)),
        err(lambda: learn(Object(1, ["only", "other"]))),
    ]

    def need(x, *args, **kwargs):
        del args, kwargs
        force(x)

    register("default", need)
    errs.append(err(lambda: learn()))
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


def demo(x, *args, **kwargs):
    del args, kwargs
    values = x.value
    return len(values), sum(values)


message = err(lambda: learn([1, 2, 3]))
register("demo", demo)
count, total = learn(Object([1, 2, 4], ["demo"]))
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "learn-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
prefix = str(message)
out.write_text(prefix + "\n" + f"n {count}\n" + f"total {total}\n")
