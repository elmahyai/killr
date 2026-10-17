import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generics.as_difftime import (
    MISSING,
    Array,
    AsDifftimeError,
    List,
    Matrix,
    Object,
    as_difftime,
    as_difftime_default,
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
        result = fn()
    except AsDifftimeError as exc:
        return exc.message
    if hasattr(result, "values") and len(result.values) == 1 and math.isnan(result.values[0]):
        return "NA"
    return "OK"


def one():
    reset_methods()
    register_s4("AccC", ("AccP",))

    def mod(tim, *args, w=1):
        del args
        values = [abs(value) for value in floats(tim)]
        return sum(values) / len(values) * w

    def sub(tim, *args, **kwargs):
        del tim, args, kwargs
        return 100

    def sq(tim, *args, **kwargs):
        del args, kwargs
        values = floats(tim)
        return math.sqrt(sum(value * value for value in values) / len(values))

    def child(tim, *args, **kwargs):
        del args, kwargs
        return floats(tim)[0] + next_method()

    def parent(tim, *args, **kwargs):
        del args, kwargs
        return sum(floats(tim))

    def double(tim, *args, **kwargs):
        del args, kwargs
        if missing(tim):
            return -8
        return sum(floats(tim)) + 1

    def integer(tim, *args, **kwargs):
        del args, kwargs
        return sum(floats(tim)) - 1

    def numeric(tim, *args, **kwargs):
        del args, kwargs
        if missing(tim):
            return -9
        return sum(floats(tim))

    def array(tim, *args, **kwargs):
        del args, kwargs
        return sum(floats(tim)) + 0.25

    def acc_p(tim, *args, **kwargs):
        del args, kwargs
        return tim.value * 2

    def default(tim, *args, **kwargs):
        del tim, args, kwargs
        return -1

    def null(tim, *args, **kwargs):
        del args, kwargs
        if missing(tim):
            return -2
        return -3

    def name(tim, *args, **kwargs):
        del args, kwargs
        if missing(tim):
            return -7
        return -6

    def strict(tim):
        return tim

    def only(tim, *args, **kwargs):
        del tim, args, kwargs
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
        as_difftime(series),
        as_difftime(series, w=2),
        as_difftime(series, 2),
        as_difftime(ti=series, w=4),
        as_difftime(Object([1, -2, 3.5], ["sub", "mod"])),
        as_difftime(Object([1, -2, 3.5], ["nope", "mod"])),
        as_difftime(Object([3, 4], ["nope", "sq"])),
        as_difftime(Object([1.5, 2.5], ["child", "parent"])),
        as_difftime([1.5, 2.5]),
        as_difftime([1, 2, 3]),
        as_difftime(Matrix([1, 2, 3, 4], 2)),
        as_difftime(Matrix([1.5, 2.5], 1)),
        as_difftime(Array([1.5, 2.5], (1, 1, 2))),
        as_difftime(Object(1.25, ["AccC"], s4=True)),
        as_difftime(Object(9, ["unknown"])),
        as_difftime(None),
        as_difftime(),
        as_difftime(z=1.5),
        as_difftime(1, tim=[1.5, 2.5]),
        as_difftime(timm=1.0),
        as_difftime(ti=[1.5, 2.5]),
        as_difftime(ti=1, tim=[1.5, 2.5]),
        as_difftime(Object("x", ["name"])),
    ]

    unregister("double", "integer", "array")
    nums.extend(
        [
            as_difftime([1.5, 2.5]),
            as_difftime([1, 2, 3]),
            as_difftime(Matrix([1.5, 2.5], 1)),
            as_difftime(Array([1.5, 2.5], (1, 1, 2))),
            as_difftime(z=1.5),
            as_difftime(tim=MISSING, z=1.5),
        ]
    )

    unregister("numeric", "NULL", "AccP", "name")
    register("default", as_difftime_default)
    errs = [
        err(lambda: as_difftime([1.5, 2.5])),
        err(lambda: as_difftime([1, 2, 3])),
        err(lambda: as_difftime(Matrix([1, 2, 3, 4], 2))),
        err(lambda: as_difftime(Array([1.5, 2.5], (1, 1, 2)))),
        err(lambda: as_difftime(True)),
        err(lambda: as_difftime("ab")),
        err(lambda: as_difftime(None)),
        err(lambda: as_difftime()),
        err(lambda: as_difftime(z=1.5)),
        err(lambda: as_difftime(z="ab")),
        err(lambda: as_difftime(Object(1, ["aa", "bb"]))),
        err(lambda: as_difftime(Object(1, [""]))),
        err(lambda: as_difftime(Object(1, ["a'b"]))),
        err(lambda: as_difftime(Object(1, ["a'b", "c"]))),
        err(lambda: as_difftime(Object(1.0, ["AccC"], s4=True))),
        err(lambda: as_difftime(List([1]))),
        err(lambda: as_difftime(1 + 2j)),
        err(lambda: as_difftime(len)),
        err(lambda: as_difftime(tim=MISSING)),
        err(lambda: as_difftime(t=1, ti=2)),
        err(lambda: as_difftime(Object(1, ["strict"]), 2)),
        err(lambda: as_difftime(Object(1, ["strict"]), 2, z=3)),
        err(lambda: as_difftime(Object(1, ["strict"]), w=4)),
        err(lambda: as_difftime(Object(1, ["only", "other"]))),
    ]

    def need(tim, *args, **kwargs):
        del args, kwargs
        force(tim)

    register("default", need)
    errs.append(err(lambda: as_difftime()))
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
register("default", as_difftime_default)


def demo(tim, *args, **kwargs):
    del args, kwargs
    values = tim.value
    return len(values), sum(values)


message = err(lambda: as_difftime([1, 2, 3]))
register("demo", demo)
count, total = as_difftime(Object([1, 2, 4], ["demo"]))
out = Path(__file__).resolve().parents[1] / "docs" / "output" / "as.difftime-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(message + "\n" + f"n {count}\n" + f"total {total}\n")
