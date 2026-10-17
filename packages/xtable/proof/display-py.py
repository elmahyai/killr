import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import Xtable
from xtable.display import display


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable([[a, b] for a, b in zip(range(1, n + 1), range(1, n + 1))])


def set_display(x: Xtable, value: object) -> Xtable:
    """Proof helper: store ``display`` like ``display<-`` after validation."""
    allowed = {"d", "f", "e", "E", "g", "G", "fg", "s"}
    if isinstance(value, str):
        vec = [value]
    else:
        vec = list(value)
    if len(vec) != x.ncol + 1:
        raise ValueError(
            f'"display" must have length equal to {x.ncol + 1} ( ncol(x) + 1 )'
        )
    if not all(v in allowed for v in vec):
        raise ValueError(
            '"display" must be in {"d","f","e","E","g","G", "fg", "s"}'
        )
    x.attrs["display"] = vec
    return x


def message_of(obj):
    try:
        return display(obj)
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
    x0 = make_xt(0)
    x0.attrs["display"] = ["s", "d", "d"]
    out["default"] = display(x0)
    specs = [
        ["d", "f", "s"],
        ["e", "E", "g"],
        ["G", "fg", "s"],
        ["s", "d", "d"],
        ["f", "f", "f"],
    ]
    for i, spec in enumerate(specs, start=1):
        x = make_xt(i)
        x = set_display(x, spec)
        out[f"disp_{i}"] = display(x)
    xwide = Xtable(
        [[r * 5 + c + 1 for c in range(5)] for r in range(3)],
        {
            "align": ["l"] * 6,
            "digits": [0] * 6,
            "display": ["s", "d", "f", "e", "G", "fg"],
        },
    )
    out["wide_preset"] = display(xwide)
    class foo:
        pass

    out["err_class"] = [message_of(foo())]
    modes = ["d", "f", "e", "E", "g", "G", "fg", "s"]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        k = x.ncol + 1
        val = [modes[(idx + j - 1) % len(modes)] for idx in range(k)]
        x = set_display(x, val)
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
