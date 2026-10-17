import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import Xtable
from xtable.display import display
from xtable.display_replacement import display_replacement
from xtable.xtable_main import RDataFrame, xtable


def make_xt(i: int):
    n = 3 + (i % 4)
    return xtable(RDataFrame({"a": list(range(1, n + 1)), "b": list(range(1, n + 1))}))


def message_of(obj):
    try:
        return display(obj)
    except ValueError as exc:
        return str(exc)


def message_of_set(kind):
    try:
        return display_replacement(make_xt(1), kind)
    except ValueError as exc:
        return str(exc)


def plain(value):
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    out = {}
    out["default"] = display(make_xt(0))
    specs = [
        ["d", "f", "s"],
        ["e", "E", "g"],
        ["G", "fg", "s"],
        ["s", "d", "d"],
        ["f", "f", "f"],
    ]
    for i, spec in enumerate(specs, start=1):
        x = make_xt(i)
        x = display_replacement(x, spec)
        out[f"disp_{i}"] = display(x)
    xwide = Xtable(
        [[r * 5 + c + 1 for c in range(5)] for r in range(3)],
        {
            "align": ["l"] * 6,
            "digits": [0] * 6,
            "display": ["s", "d", "f", "e", "G", "fg"],
        },
        classes=("xtable", "matrix"),
    )
    out["wide_preset"] = display(xwide)

    class foo:
        pass

    out["err_class"] = [message_of(foo())]
    out["err_len"] = [message_of_set(["d", "f"])]
    out["err_mode"] = [message_of_set(["d", "f", "x"])]
    modes = ["d", "f", "e", "E", "g", "G", "fg", "s"]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        k = x.ncol + 1
        val = [modes[(idx + j - 1) % len(modes)] for idx in range(k)]
        x = display_replacement(x, val)
        attr = display(x)
        if isinstance(attr, list):
            repeated.extend(attr)
        elif attr is not None:
            repeated.append(attr)
    out["repeated"] = repeated
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
