import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption import caption
from xtable.caption_replacement import NA, Xtable, caption_replacement

example = Path("/home/ahmed/killr_projects/killr/packages/xtable/docs/output/caption-python.txt")


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable([[a, b] for a, b in zip(range(1, n + 1), range(1, n + 1))])


def message_of(obj):
    try:
        return caption(obj)
    except ValueError as exc:
        return str(exc)


def print_caption(value):
    if value is None:
        return "NULL"
    if isinstance(value, list):
        if not value:
            return "character(0)"
        parts = []
        for v in value:
            if v is NA:
                parts.append("NA")
            else:
                parts.append(f'"{v}"')
        return "[1] " + "  ".join(parts)
    if value is NA:
        return "[1] NA"
    return f'[1] "{value}"'


x = make_xt(0)
caption_replacement(x, "Table caption for the example")
lines = [print_caption(caption(x))]
caption_replacement(x, ["First line", "Second line"])
lines.append(print_caption(caption(x)))
example.write_text("\n".join(lines) + "\n")


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    out = {}
    caps = [
        "A short caption",
        ["Line one", "Line two"],
        [],
        NA,
        NA,
        "café & naïve",
        "",
        ["", "second"],
    ]
    for i, cap in enumerate(caps, start=1):
        x = make_xt(i)
        x = caption_replacement(x, cap)
        out[f"cap_{i}"] = caption(x)
    xmat = Xtable(
        [[r * 4 + c + 1 for c in range(4)] for r in range(3)],
        {
            "align": ["l"] * 5,
            "digits": [0] * 5,
            "display": ["d"] * 5,
        },
    )
    xmat = caption_replacement(xmat, "matrix table")
    out["matrix_cap"] = caption(xmat)
    out["int_cap"] = caption(caption_replacement(make_xt(99), [1, 2]))
    class foo:
        pass

    out["err_class"] = [message_of(foo())]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        x = caption_replacement(x, f"cap-{j}")
        cap = caption(x)
        if isinstance(cap, list):
            repeated.extend(cap)
        elif cap is not None:
            repeated.append(cap)
    out["repeated"] = repeated
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
