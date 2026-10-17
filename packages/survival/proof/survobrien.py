import statistics
import time

from survival.survobrien import survobrien


OVARIAN = {
    "futime": [
        59, 115, 156, 421, 431, 448, 464, 475, 477, 563, 638, 744, 769, 770, 803, 855,
        1040, 1106, 1129, 1206, 1227, 268, 329, 353, 365, 377,
    ],
    "fustat": [
        1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0,
    ],
    "age": [
        72.331500000000005, 74.493200000000002, 66.465800000000002, 53.364400000000003,
        50.339700000000001, 56.430100000000003, 56.936999999999998, 59.854799999999997,
        64.175299999999993, 55.178100000000001, 56.7562, 50.1096, 59.630099999999999,
        57.052100000000003, 39.2712, 43.1233, 38.8932, 44.600000000000001,
        53.906799999999997, 44.205500000000001, 59.588999999999999, 74.504099999999994,
        43.137, 63.219200000000001, 64.424700000000001, 58.309600000000003,
    ],
    "resid.ds": [2, 2, 2, 2, 2, 1, 2, 2, 2, 1, 1, 1, 2, 2, 1, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1],
    "rx": [1, 1, 1, 2, 1, 1, 2, 2, 1, 2, 1, 2, 2, 2, 1, 1, 1, 1, 2, 2, 2, 1, 1, 2, 2, 2],
    "ecog.ps": [1, 1, 2, 1, 1, 2, 2, 2, 1, 2, 2, 1, 2, 1, 1, 2, 2, 1, 1, 1, 2, 2, 1, 2, 1, 1],
}


def serialize(frame):
    out = ["|".join(frame.names)]
    for name, col in zip(frame.names, frame.columns):
        if hasattr(col, "codes"):
            col = [int(c) if c is not None else None for c in col.codes]
        if isinstance(col, (list, tuple)):
            tokens = []
            for value in col:
                if value is None:
                    tokens.append("NA")
                elif isinstance(value, float):
                    tokens.append(f"{value:.17g}")
                else:
                    tokens.append(str(value))
            out.append(",".join(tokens))
        else:
            out.append(",".join(f"{v:.17g}" for v in col))
    return out


def one():
    xx = survobrien(
        "Surv(futime, fustat) ~ age + factor(rx) + I(ecog.ps)",
        data=OVARIAN,
    )
    return serialize(xx)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
