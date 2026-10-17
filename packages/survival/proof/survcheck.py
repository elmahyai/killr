import statistics
import time

from survival.fromtimeline import Categorical
from survival.survcheck import survcheck


def one():
    tdata = {
        "id": [1, 1, 1, 2, 2, 2],
        "tstart": [0, 5, 12, 0, 5, 11],
        "tstop": [5, 10, 15, 5, 10, 14],
        "event": Categorical(["a", "b", "censor", "a", "b", "censor"], ["censor", "a", "b"]),
    }
    fit = survcheck("Surv(tstart, tstop, event) ~ 1", tdata, id="id")
    trans = fit["transitions"]
    gap = fit.get("gap")
    gap_line = (
        "gap:NA"
        if gap is None
        else f"gap:{','.join(str(int(x)) for x in gap['row'])};{','.join(str(x) for x in gap['id'])}"
    )
    return [
        "|".join(fit["states"]),
        "|".join(f"{name}={fit['flag'][name]:.17g}" for name in fit["flag"]),
        ",".join(str(fit["n"][key]) for key in ("id", "observations", "transitions")),
        ",".join(f"{value:.17g}" for value in trans.reshape(-1, order="F")),
        f"{trans.shape[0]}x{trans.shape[1]}",
        "|".join(fit["istate"].values),
        gap_line,
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
