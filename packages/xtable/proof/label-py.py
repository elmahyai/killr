import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import NA, Xtable
from xtable.label import label

LOGICAL_NA = object()

example = Path("/home/ahmed/killr_projects/killr/packages/xtable/docs/output/label-python.txt")


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable([[a, b] for a, b in zip(range(1, n + 1), range(1, n + 1))])


def _r_length(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def set_label(x: Xtable, value: object) -> Xtable:
    if _r_length(value) > 1:
        raise ValueError('"label" must have length 1')
    if isinstance(value, (list, tuple)) and len(value) == 0:
        x.attrs["label"] = []
    elif value is NA:
        x.attrs["label"] = [NA]
    elif value is LOGICAL_NA:
        x.attrs["label"] = [LOGICAL_NA]
    elif isinstance(value, (list, tuple)):
        x.attrs["label"] = list(value)
    elif isinstance(value, int):
        x.attrs["label"] = [value]
    else:
        x.attrs["label"] = [value]
    return x


def message_of(obj):
    try:
        return label(obj)
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
set_label(x, "tab:example")
lines = [print_label(label(x))]
set_label(x, [])
lines.append(print_label(label(x)))
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
        x = set_label(x, lab)
        out[f"lab_{i}"] = label(x)
    xmat = Xtable(
        [[r * 4 + c + 1 for c in range(4)] for r in range(3)],
        {
            "align": ["l"] * 5,
            "digits": [0] * 5,
            "display": ["d"] * 5,
        },
    )
    xmat = set_label(xmat, "tab:matrix")
    out["matrix_lab"] = label(xmat)

    def err_len():
        try:
            set_label(make_xt(99), [1, 2])
        except ValueError as exc:
            return str(exc)
        raise AssertionError("expected length error")

    out["err_len"] = [err_len()]

    class foo:
        pass

    out["err_class"] = [message_of(foo())]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        x = set_label(x, f"tab-{j}")
        val = label(x)
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
