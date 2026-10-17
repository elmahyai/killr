import json
import math
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr")

from httr.headers import (
    NA,
    NA_NAME,
    Atomic,
    Date,
    Dot,
    Factor,
    POSIXct,
    add_headers,
)


def enc(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def show_headers(headers):
    if headers is None:
        return "NULL"
    if len(headers.values) == 0:
        return "character(0)"
    parts = []
    for name, value in zip(headers.names, headers.values):
        shown_name = "<NA>" if name is NA_NAME else enc(name)
        shown_value = "<NA>" if value is None else enc(value)
        parts.append(shown_name + "=" + shown_value)
    return "|".join(parts)


def line(fn):
    try:
        result = fn()
    except ValueError as exc:
        return "ERR " + str(exc)
    return (
        "class="
        + "/".join(result.classes)
        + "|method="
        + ("NULL" if result.method is None else "SET")
        + "|url="
        + ("NULL" if result.url is None else "SET")
        + "|fields="
        + ("NULL" if result.fields is None else "SET")
        + "|options="
        + ("NULL" if result.options is None else "SET")
        + "|auth="
        + ("NULL" if result.auth_token is None else "SET")
        + "|output="
        + ("NULL" if result.output is None else "SET")
        + "|headers="
        + show_headers(result.headers)
    )


def character(*values, names=None):
    return Atomic(list(values), "character", names)


def one():
    instant = POSIXct([946684800.0], tz="UTC")
    day = Date([10957.0])
    calls = [
        lambda: add_headers(a=1, b=2),
        lambda: add_headers(**{".headers": character("1", "2", names=["a", "b"])}),
        lambda: add_headers(),
        lambda: add_headers(Dot(1, "x"), Dot(2, "x")),
        lambda: add_headers(Dot(1, "b"), Dot(2, "a"), Dot(3, "b")),
        lambda: add_headers(x=1, **{".headers": character("9", "3", names=["x", "y"])}),
        lambda: add_headers(
            Dot(1, "a"),
            Dot(3, "c"),
            **{".headers": character("2", names=["b"])},
        ),
        lambda: add_headers("hello"),
        lambda: add_headers("hello", "world"),
        lambda: add_headers(Dot(1, "a"), 2, Dot(3, "b")),
        lambda: add_headers(Dot(1, "a"), 2, 4, Dot(3, "b")),
        lambda: add_headers(character("1", "2", names=["a", "b"])),
        lambda: add_headers(foo=character("1", "2", names=["a", "b"])),
        lambda: add_headers(foo=character("1", "2")),
        lambda: add_headers(foo="1"),
        lambda: add_headers(a=None, b="2"),
        lambda: add_headers(a=character(), b="2"),
        lambda: add_headers(a=None),
        lambda: add_headers(**{".headers": None}),
        lambda: add_headers(**{".headers": character()}),
        lambda: add_headers(**{".headers": Atomic([], "double")}),
        lambda: add_headers(Atomic([], "double")),
        lambda: add_headers(**{".headers": Atomic([1.0], "double", ["a"])}),
        lambda: add_headers(a=1, b=2.5),
        lambda: add_headers(a=True, b=False, c=NA),
        lambda: add_headers(
            a=Atomic([None], "integer"),
            b=Atomic([None], "double"),
            c=Atomic([None], "character"),
            d=float("nan"),
            e=float("inf"),
            f=float("-inf"),
        ),
        lambda: add_headers(a=-0.0),
        lambda: add_headers(
            a=1e-4,
            b=1e5,
            c=100000.0,
            d=0.0001,
            e=9999999.0,
            f=1e6,
            g=1.23e-10,
            h=1e20,
            i=1e-20,
        ),
        lambda: add_headers(
            a=1.1,
            b=math.pi,
            c=1 / 3,
            d=2 / 3,
            e=float(2**53),
            f=float(2**53 + 1),
        ),
        lambda: add_headers(a=1 + 2j),
        lambda: add_headers(
            a=0 + 1j,
            b=1 - 2j,
            c=-1 - 2j,
            d=Atomic([(None, 0.0)], "complex"),
            e=Atomic([(float("nan"), 0.0)], "complex"),
            f=Atomic([(float("inf"), 1.0)], "complex"),
            g=1.5 + 2.5j,
            h=Atomic([(1e-4, 1e5)], "complex"),
            i=Atomic([(-0.0, 0.0)], "complex"),
            j=0j,
        ),
        lambda: add_headers(a=Factor(["b"], ["a", "b"])),
        lambda: add_headers(a=Atomic([True, False, None], "logical")),
        lambda: add_headers(a=Atomic([1, 2, 3], "integer")),
        lambda: add_headers(a=Atomic([1, 0], "integer")),
        lambda: add_headers(**{".headers": character("1", "2", names=["a", NA_NAME])}),
        lambda: add_headers(
            **{".headers": character("1", "2", "3", names=["a", NA_NAME, NA_NAME])}
        ),
        lambda: add_headers(**{".headers": character("1", "2", names=[NA_NAME, "NA"])}),
        lambda: add_headers(a="", b="x"),
        lambda: add_headers(**{".head": "x"}),
        lambda: add_headers(headers="x"),
        lambda: add_headers(**{".headers": character("x", names=[".headers"])}),
        lambda: add_headers(a=[1]),
        lambda: add_headers(**{".headers": [1]}),
        lambda: add_headers(a=bytes([65])),
        lambda: add_headers(a=bytes([0, 10, 65, 255])),
        lambda: add_headers(**{".headers": bytes([65])}),
        lambda: add_headers(Accept=""),
        lambda: add_headers(Dot("1", "A"), Dot("2", "a"), Dot("3", "A")),
        lambda: add_headers(
            Dot(1, "a"), Dot(2, "a"), Dot(3, "a"), Dot(4, "b"), Dot(5, "a")
        ),
        lambda: add_headers(**{".headers": Atomic(["a", "b"], "character", dim=(1, 2))}),
        lambda: add_headers(
            a="z",
            **{".headers": Atomic(["a", "b"], "character", dim=(1, 2))},
        ),
        lambda: add_headers(a=object()),
        lambda: add_headers(
            **{".headers": character("1", "2", "3", names=["a", "b", "a"])}
        ),
        lambda: add_headers(1, a=2),
        lambda: add_headers(a=Atomic([1.0, 2.0], "double", ["x", "y"])),
        lambda: add_headers(A=Atomic([1.0], "double", ["x"])),
        lambda: add_headers(**{".headers": character("p", "q", names=["", "b"])}),
        lambda: add_headers(**{".headers": Atomic([], "character", [])}),
        lambda: add_headers(a=1e-4 / 1000**-2),
        lambda: add_headers(
            a=sys.float_info.epsilon,
            b=sys.float_info.min,
            c=sys.float_info.max,
        ),
        lambda: add_headers(
            a=123456789012345.0,
            b=1.23456789012345e-7,
            c=0.000123456789012345,
            d=9.99e-5,
        ),
        lambda: add_headers(n=Atomic([1.0, None, 3.0], "double")),
        lambda: add_headers(**{".headers": character(None, "ok", names=["a", "b"])}),
        lambda: add_headers(
            Dot("na", "a"),
            Dot("xx", "b"),
            **{".headers": character("nb", "nc", names=["a", "c"])},
        ),
        lambda: add_headers(A=character("1", "2", "3", names=["", "b", NA_NAME])),
        lambda: add_headers(A=character("1", "2", names=[NA_NAME, NA_NAME])),
        lambda: add_headers(foo=Atomic(list(range(1, 11)), "integer")),
        lambda: add_headers(A=character("1", "2", names=["x", ""])),
        lambda: add_headers(
            **{".headers": character("1", "2", "3", names=["", "", ""])}
        ),
        lambda: add_headers(
            **{".headers": character("1", "2", "3", names=["", "", " "])}
        ),
        lambda: add_headers(**{"a b": "c", "ü": "d", "a:b": "e"}),
        lambda: add_headers(a="x\ny"),
        lambda: add_headers(
            **{
                ".headers": Atomic(
                    ["1", "2"], "character", ["a", "b"], classes=("foo",)
                )
            }
        ),
        lambda: add_headers(**{".headers": Atomic([True], "logical", ["a"])}),
        lambda: add_headers(a=1, **{".headers": None}),
        lambda: add_headers(a="1", **{".headers": None}),
        lambda: add_headers(a="1", **{".headers": Atomic([2.0], "double", ["b"])}),
        lambda: add_headers(Atomic([1.0, 2.0, 3.0], "double", ["x", "x", "y"])),
        lambda: add_headers(A=Atomic([1.0, 2.0], "double", ["x", "x"])),
        lambda: add_headers(Dot("z", "a"), 1, 2),
        lambda: add_headers(1, 2, 3),
        lambda: add_headers(a=instant),
        lambda: add_headers(a=instant, b="1"),
        lambda: add_headers(a="1", b=instant),
        lambda: add_headers(a=None, b=instant),
        lambda: add_headers(a=character(), b=instant),
        lambda: add_headers(a=day),
        lambda: add_headers(a=day, b="1"),
        lambda: add_headers(a="1", b=day),
        lambda: add_headers(a=instant, b="2000-01-01"),
        lambda: add_headers(a=instant, b="2000-01-01 extra"),
        lambda: add_headers(a=instant, b="nope"),
        lambda: add_headers(**{".headers": Factor(["a", "b"], ["a", "b"])}),
        lambda: add_headers(a=Factor(["x", "y"], ["x", "y"])),
        lambda: add_headers(bytes()),
        lambda: add_headers(a=[]),
        lambda: add_headers(A=character("1", names=[""])),
        lambda: add_headers(A=character("1", names=[NA_NAME])),
        lambda: add_headers(**{".headers": character("1", "2", names=["a", ""])}),
    ]
    return "\n".join(line(fn) for fn in calls)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
