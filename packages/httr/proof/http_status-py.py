import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr")

from httr.status import (
    MISSING,
    NA_NAME,
    LogicalNA,
    Numeric,
    Response,
    http_status,
)

CODES = (
    100, 101, 102,
    200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
    300, 301, 302, 303, 304, 305, 306, 307, 308,
    400, 401, 402, 403, 404, 405, 406, 407, 408, 409,
    410, 411, 412, 413, 414, 415, 416, 417, 418, 420,
    422, 423, 424, 425, 426, 428, 429, 431, 444, 449,
    450, 451, 499,
    500, 501, 502, 503, 504, 505, 506, 507, 508, 509,
    510, 511, 598, 599,
)


def show(value):
    return (
        "category="
        + value.category
        + "|reason="
        + value.reason
        + "|message="
        + value.message
    )


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


def r_print(value):
    chunks = []
    for name in ("category", "reason", "message"):
        chunks.append("$" + name + "\n" + '[1] "' + getattr(value, name) + '"\n\n')
    return "".join(chunks)


def one():
    lines = [show(http_status(float(code))) for code in CODES]
    lines.extend(
        [
            show(http_status(200)),
            show(http_status(424)),
            show(http_status(Numeric([404.0], names=("a",)))),
            show(http_status(Numeric([404.0], comment="hi"))),
            show(http_status(Numeric([404.0], names=("code",)))),
            show(http_status(Numeric([404.0], dim=(1, 1)))),
            show(http_status(Numeric([404.0], dim=(1, 1, 1)))),
            show(http_status(Numeric([404.0], classes=("numeric",)))),
            show(
                http_status(
                    Numeric([404], kind="integer", classes=("integer", "numeric"))
                )
            ),
            show(http_status(std(404))),
            show(http_status(std(200.0))),
            show(http_status(Response([("status_codes", 404)]))),
            show(
                http_status(
                    Response([("status_code", 404), ("status_code", 200)])
                )
            ),
            show(http_status(199.99999999999997)),
            show(http_status(200.00000000000003)),
            grab(lambda: http_status(320.0)),
            grab(lambda: http_status(0.0)),
            grab(lambda: http_status(99.0)),
            grab(lambda: http_status(103.0)),
            grab(lambda: http_status(404.5)),
            grab(lambda: http_status(600.0)),
            grab(lambda: http_status(-1.0)),
            grab(lambda: http_status(Numeric([MISSING], kind="double"))),
            grab(lambda: http_status(Numeric([MISSING], kind="integer"))),
            grab(lambda: http_status(float("nan"))),
            grab(lambda: http_status(float("inf"))),
            grab(lambda: http_status(float("-inf"))),
            grab(lambda: http_status(-0.0)),
            grab(lambda: http_status(None)),
            grab(lambda: http_status("404")),
            grab(lambda: http_status(True)),
            grab(lambda: http_status(False)),
            grab(lambda: http_status(Numeric([404.0, 200.0]))),
            grab(lambda: http_status(Numeric([404, 200], kind="integer"))),
            grab(lambda: http_status(Numeric([], kind="double"))),
            grab(lambda: http_status(Numeric([], kind="integer"))),
            grab(lambda: http_status(Numeric([404.0, 200.0], dim=(1, 2)))),
            grab(lambda: http_status(99.99999999999999)),
            grab(lambda: http_status(std(None))),
            grab(lambda: http_status(std("404"))),
            grab(lambda: http_status(std("320"))),
            grab(lambda: http_status(std(""))),
            grab(lambda: http_status(std(Numeric([MISSING], kind="double")))),
            grab(lambda: http_status(std(Numeric([MISSING], kind="integer")))),
            grab(lambda: http_status(std(float("nan")))),
            grab(lambda: http_status(std(Numeric([404.0, 200.0])))),
            grab(
                lambda: http_status(
                    Response([("status_code_a", 1), ("status_code_b", 2)])
                )
            ),
            grab(lambda: http_status(Response([]))),
            grab(lambda: http_status(Response([("status", 404)]))),
            grab(lambda: http_status(Response([("Status_code", 404)]))),
            grab(lambda: http_status(Response([(NA_NAME, 5)]))),
            grab(lambda: http_status(std([404.0]))),
            grab(lambda: http_status(std(True))),
            grab(lambda: http_status(std(200 + 0j))),
            grab(lambda: http_status(std(Numeric([], kind="character")))),
            grab(lambda: http_status([404.0])),
            grab(
                lambda: http_status(
                    Numeric([1], kind="integer", classes=("factor",))
                )
            ),
            grab(lambda: http_status(LogicalNA())),
        ]
    )
    return "\n".join(lines)


example = r_print(http_status(100.0)) + r_print(http_status(404.0))
with open(
    "/home/ahmed/killr_projects/killr/packages/httr/docs/output/http_status-python.txt",
    "w",
    encoding="utf-8",
) as handle:
    handle.write(example)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
