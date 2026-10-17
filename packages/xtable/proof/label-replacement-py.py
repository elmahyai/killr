import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import NA, Xtable
from xtable.label import label, label_attr
from xtable.label_replacement import label_replacement

LOGICAL_NA = object()

example = Path(
    "/home/ahmed/killr_projects/killr/packages/xtable/docs/output/label-replacement-python.txt"
)


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable([[a, b] for a, b in zip(range(1, n + 1), range(1, n + 1))])


def message_of(kind):
    try:
        return label_replacement(make_xt(1), kind)
    except ValueError as exc:
        return str(exc)


def print_label(value):
    if value is None:
        return "NULL"
    if isinstance(value, list):
        if not value:
            return "character(0)"
        parts = []
        for v in value:
            if v is NA:
                parts.append("NA")
            elif v is LOGICAL_NA:
                parts.append("NA")
            elif isinstance(v, int):
                parts.append(str(v))
            else:
                parts.append(f'"{v}"')
        return "[1] " + "  ".join(parts)
    if value is NA:
        return "[1] NA"
    if isinstance(value, int):
        return f"[1] {value}"
    return f'[1] "{value}"'


x = make_xt(0)
label_replacement(x, "tab:example")
lines = [print_label(label(x))]
label_replacement(x, [])
lines.append(print_label(label(x)))
example.parent.mkdir(parents=True, exist_ok=True)
example.write_text("\n".join(lines) + "\n")


def plain(value):
    if value is NA or value is LOGICAL_NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def one():
    out = {}
    labs = [
        "tab:short",
        [],
        NA,
        LOGICAL_NA,
        "café_label",
        "",
        42,
        ["tab:vector"],
    ]
    for i, lab in enumerate(labs, start=1):
        x = make_xt(i)
        x = label_replacement(x, lab)
        out[f"lab_{i}"] = label_attr(x)
    xmat = Xtable(
        [[r * 4 + c + 1 for c in range(4)] for r in range(3)],
        {
            "align": ["l"] * 5,
            "digits": [0] * 5,
            "display": ["d"] * 5,
        },
    )
    xmat = label_replacement(xmat, "tab:matrix")
    out["matrix_lab"] = label_attr(xmat)
    out["err_len"] = [message_of([1, 2])]
    class foo:
        pass

    try:
        label_replacement(foo(), "x")
        out["err_class"] = None
    except ValueError as exc:
        out["err_class"] = [str(exc)]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        x = label_replacement(x, f"tab-{j}")
        val = label_attr(x)
        if isinstance(val, list):
            repeated.extend(plain(val))
        elif val is not None:
            repeated.append(plain(val))
    out["repeated"] = repeated
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"median_ms": statistics.median(elapsed), "value": plain(value)}))
