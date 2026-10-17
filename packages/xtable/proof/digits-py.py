import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.caption_replacement import Xtable
from xtable.digits import digits


def make_xt(i: int) -> Xtable:
    n = 3 + (i % 4)
    return Xtable([[a, b] for a, b in zip(range(1, n + 1), range(1, n + 1))])


def set_digits(x: Xtable, value: object) -> Xtable:
    """Proof helper: store ``digits`` like ``digits<-`` after validation."""
    ncol = x.ncol
    if isinstance(value, list) and value and isinstance(value[0], list):
        matrix = value
        if len(matrix[0]) != ncol + 1 or len(matrix) != x.nrow:
            raise ValueError(
                "if argument 'digits' is a matrix, it must have columns equal "
                f"to {ncol + 1} ( ncol(x) + 1 ) and rows equal to {x.nrow} "
                f"( nrow( x )"
            )
        x.attrs["digits"] = [list(row) for row in matrix]
    else:
        if isinstance(value, (list, tuple)):
            vec = list(value)
        else:
            vec = [value]
        if len(vec) == 1:
            vec = vec * (ncol + 1)
        elif len(vec) > 1 and len(vec) != ncol + 1:
            raise ValueError(
                "if argument 'digits' is a vector of length more than one, "
                f"it must have length equal to {ncol + 1} ( ncol(x) + 1 )"
            )
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vec):
            raise ValueError('"digits" must be numeric')
        x.attrs["digits"] = vec
    return x


def message_of(obj):
    try:
        return digits(obj)
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
    x0 = make_xt(0)
    x0.attrs["digits"] = [0, 2, 2]
    out["default"] = digits(x0)
    specs = [
        4,
        [1, 2, 3],
        [0, 0, 0],
        [5, 4, 3],
        0,
    ]
    for i, spec in enumerate(specs, start=1):
        x = make_xt(i)
        x = set_digits(x, spec)
        out[f"dig_{i}"] = digits(x)
    xmat = Xtable(
        [[r * 4 + c + 1 for c in range(4)] for r in range(3)],
        {
            "align": ["l"] * 5,
            "digits": [0] * 5,
            "display": ["d"] * 5,
        },
    )
    xmat = set_digits(
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
    )
    out["wide_preset"] = digits(xwide)
    class foo:
        pass

    out["err_class"] = [message_of(foo())]
    repeated = []
    for j in range(1, 401):
        x = make_xt(j)
        x = set_digits(x, j % 7)
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
