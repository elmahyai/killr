import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.digits import digits
from xtable.digits_replacement import digits_replacement
from xtable.xtable_main import RDataFrame, xtable


def make_xt(i: int):
    n = 3 + (i % 4)
    return xtable(RDataFrame({"a": list(range(1, n + 1)), "b": list(range(1, n + 1))}))


def message_of(obj):
    try:
        return digits(obj)
    except ValueError as exc:
        return str(exc)


def message_of_set(kind):
    try:
        return digits_replacement(make_xt(1), kind)
    except ValueError as exc:
        return str(exc)


def plain(value):
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            return [plain(row) for row in value]
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    out = {}
    out["default"] = digits(make_xt(0))
    specs = [
        4,
        [1, 2, 3],
        [0, 0, 0],
        [5, 4, 3],
        0,
    ]
    for i, spec in enumerate(specs, start=1):
        x = make_xt(i)
        x = digits_replacement(x, spec)
        out[f"dig_{i}"] = digits(x)
    from xtable.caption_replacement import Xtable

    xmat = Xtable(
        [[r * 4 + c + 1 for c in range(4)] for r in range(3)],
        {
            "align": ["l"] * 5,
            "digits": [0] * 5,
            "display": ["d"] * 5,
        },
        classes=("xtable", "matrix"),
    )
    xmat = digits_replacement(
        xmat, [[c * 3 + r + 1 for c in range(5)] for r in range(3)]
    )
    out["matrix_dig"] = digits(xmat)
    xwide = Xtable(
        [[r * 3 + c + 1 for c in range(3)] for r in range(2)],
        {
            "align": ["l"] * 4,
            "digits": [[1, 3, 5, 7], [2, 4, 6, 8]],
            "display": ["d"] * 4,
        },
        classes=("xtable", "matrix"),
    )
    out["wide_preset"] = digits(xwide)

    class foo:
        pass

    out["err_class"] = [message_of(foo())]
    out["err_len"] = [message_of_set([1, 2])]
    out["err_numeric"] = [message_of_set(["a", "b", "c"])]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        x = digits_replacement(x, j % 7)
        val = digits(x)
        if isinstance(val, list):
            if val and isinstance(val[0], list):
                for row in val:
                    repeated.extend(row)
            else:
                repeated.extend(val)
    out["repeated"] = repeated
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
