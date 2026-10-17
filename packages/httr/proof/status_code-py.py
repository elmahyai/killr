import json
import math
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr")

from httr.status import MISSING, NA_NAME, LogicalNA, Numeric, Response, status_code


def fmt_double(value):
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if value is MISSING:
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0 and math.copysign(1.0, value) < 0:
        return "-0"
    return format(value, ".17g")


def show(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "logical[" + ("TRUE" if value else "FALSE") + "]"
    if isinstance(value, int):
        return f"integer[{value}]"
    if isinstance(value, float):
        return "double[" + fmt_double(value) + "]"
    if isinstance(value, str):
        return "character[" + value + "]"
    if isinstance(value, list):
        return "list[" + ",".join(show(item) for item in value) + "]"
    if isinstance(value, Response):
        parts = []
        for name, item in value.fields:
            body = show(item)
            if name is NA_NAME:
                parts.append("NA_NAME=" + body)
            elif isinstance(name, str) and name:
                parts.append(name + "=" + body)
            else:
                parts.append(body)
        extra = ""
        if value.classes:
            extra = " class=" + "/".join(value.classes)
        return "list[" + ",".join(parts) + "]" + extra
    if isinstance(value, Numeric):
        if value.kind == "double":
            vals = ",".join(fmt_double(item) for item in value.values)
        elif value.kind == "integer":
            vals = ",".join("NA" if item is MISSING else str(item) for item in value.values)
        else:
            vals = ",".join("NA" if item is MISSING else item for item in value.values)
        extra = ""
        if value.names is not None:
            extra += " names=" + "|".join(value.names)
        if value.dim is not None:
            extra += " dim=" + ",".join(str(item) for item in value.dim)
        if value.dimnames is not None:
            bits = []
            for margin in value.dimnames:
                bits.append("" if margin is None else "|".join(margin))
            extra += " dimnames=" + ";".join(bits)
        if value.comment is not None:
            extra += " comment=" + value.comment
        if value.classes is not None:
            extra += " class=" + "/".join(value.classes)
        return value.kind + "[" + vals + "]" + extra
    return "OTHER " + type(value).__name__


def grab(fn):
    try:
        return show(fn())
    except ValueError as exc:
        return "ERR " + str(exc)


def std(code):
    return Response(
        [
            ("url", "http://example.test/status/404"),
            ("status_code", code),
            ("headers", []),
        ]
    )


def one():
    named = Numeric([200.0, 404.0], names=("a", "b"))
    kept = Numeric([404], kind="integer", comment="kept")
    mat = Numeric(
        [200.0, 404.0],
        dim=(1, 2),
        dimnames=(("row",), ("a", "b")),
    )
    imat = Numeric([200, 404], kind="integer", dim=(1, 2))
    arr = Numeric([1.0, 2.0, 3.0, 4.0], dim=(1, 2, 2))
    dim1 = Numeric([1, 2, 3], kind="integer", dim=(3,))
    commented = Numeric([200], kind="integer", comment="hi")
    classed_num = Numeric([7.0], classes=("numeric",))
    classed_int = Numeric([1], kind="integer", classes=("integer", "numeric"))
    num_first = Response([("status_code", 9.0)], classes=("numeric", "response"))
    resp_first = Response([("status_code", 3)], classes=("response", "numeric"))
    foo_resp = Response([("status_code", 201)], classes=("foo", "response"))
    na_name = Response([(NA_NAME, 5)], classes=("response",))
    na_partial = Response(
        [(NA_NAME, 1), ("status_code_x", 6)],
        classes=("response",),
    )
    lines = [
        show(status_code(std(404))),
        show(status_code(std(404.0))),
        show(status_code(std(200.5))),
        show(status_code(std(Numeric([MISSING], kind="integer")))),
        show(status_code(std(Numeric([MISSING], kind="double")))),
        show(status_code(std(float("nan")))),
        show(status_code(std(-0.0))),
        show(status_code(std(kept))),
        show(status_code(std(named))),
        show(status_code(std([1.0, 2.0]))),
        show(status_code(std("404"))),
        show(status_code(std(None))),
        show(
            status_code(
                Response(
                    [
                        ("url", "http://example.test/status/404"),
                        ("headers", []),
                    ]
                )
            )
        ),
        show(status_code(Response([]))),
        show(status_code(Response([("status_code_extra", 222)]))),
        show(status_code(Response([("status_code_a", 1), ("status_code_b", 2)]))),
        show(status_code(Response([("status_code", 10), ("status_code_extra", 11)]))),
        show(status_code(Response([("status_code_extra", 1), ("status_code", 2)]))),
        show(status_code(Response([("status_code", 1), ("status_code", 2)]))),
        show(status_code(Response([("status", 33)]))),
        show(status_code(Response([("Status_code", 3)]))),
        show(status_code(Response([("status_codes", 5)]))),
        show(status_code(na_name)),
        show(status_code(na_partial)),
        show(status_code(200.0)),
        show(status_code(200)),
        show(status_code(Numeric([200.0, 404.0, MISSING]))),
        show(status_code(Numeric([200.0, 404.5], names=("a", "b")))),
        show(status_code(Numeric([], kind="double"))),
        show(status_code(Numeric([], kind="integer"))),
        show(status_code(Numeric([MISSING], kind="double"))),
        show(status_code(float("nan"))),
        show(status_code(Numeric([float("inf"), float("-inf")]))),
        show(status_code(-0.0)),
        show(status_code(commented)),
        show(status_code(mat)),
        show(status_code(imat)),
        show(status_code(arr)),
        show(status_code(dim1)),
        show(status_code(classed_num)),
        show(status_code(classed_int)),
        show(status_code(num_first)),
        show(status_code(resp_first)),
        show(status_code(foo_resp)),
        grab(lambda: status_code(LogicalNA())),
        grab(lambda: status_code(None)),
        grab(lambda: status_code("404")),
        grab(lambda: status_code(True)),
        grab(lambda: status_code([200])),
        grab(lambda: status_code(Numeric([1], kind="integer", classes=("factor",)))),
        grab(lambda: status_code(Numeric([200], kind="integer", classes=("raw",)))),
        grab(lambda: status_code(Numeric([200.0], classes=("complex",)))),
        grab(lambda: status_code(Numeric([200.0], classes=("ts",)))),
        grab(lambda: status_code(Numeric([200.0], classes=("integer",)))),
        grab(lambda: status_code(Numeric([1.0], classes=("double",)))),
        grab(lambda: status_code(Numeric([1.0], dim=(1, 1), classes=("matrix",)))),
        grab(lambda: status_code(Numeric([1.0], classes=("foo", "bar")))),
        grab(lambda: status_code(Numeric(["a"], kind="character", dim=(1, 1)))),
        grab(lambda: status_code(Numeric([404], kind="integer", classes=("response",)))),
    ]
    return "\n".join(lines)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
