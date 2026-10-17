import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.simulatelme import fingerprint_simulate_lme, simulate_lme


def one():
    sim = simulate_lme(
        {
            "fixed": "distance ~ age",
            "data": "Orthodont",
            "random": "~ 1 | Subject",
        },
        nsim=3,
        seed=42,
        m2={"random": "~ age | Subject"},
    )
    return fingerprint_simulate_lme(sim)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
