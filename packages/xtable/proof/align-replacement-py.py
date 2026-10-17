import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.align_replacement import align_attr, align_replacement
from xtable.caption_replacement import Xtable


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable([[a, b] for a, b in zip(range(1, n + 1), range(1, n + 1))])


def message_of(kind):
    try:
        return align_replacement(make_xt(1), kind)
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
    specs = [
        ["l", "l", "l"],
        "lll",
        "l{2in}ll",
        ["l", "|", "l", "l"],
        ["r", "r", "r"],
        "lcr",
    ]
    for i, spec in enumerate(specs, start=1):
        x = make_xt(i)
        x = align_replacement(x, spec)
        out[f"align_{i}"] = align_attr(x)
    xwide = Xtable(
        [[r * 5 + c + 1 for c in range(5)] for r in range(3)],
        {
            "align": ["l"] * 6,
            "digits": [0] * 6,
            "display": ["d"] * 6,
        },
    )
    xwide = align_replacement(xwide, ["l", "c", "c", "c", "c", "c"])
    out["wide"] = align_attr(xwide)
    out["err_len"] = [message_of(["l", "l"])]
    class foo:
        pass

    try:
        align_replacement(foo(), "lll")
        out["err_class"] = None
    except ValueError as exc:
        out["err_class"] = [str(exc)]
    out["err_brace"] = [message_of("l{2in")]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        val = "l" * (x.ncol + 1)
        x = align_replacement(x, val)
        attr = align_attr(x)
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
