"""dqrdc2 kernel of nlmegls: l_rss from gls_loglik for each case in data/dqrdc2-cases.txt.

Matches dqrdc2-r.R. Only the loop over the cases is timed; the untimed call comes first.
"""

import statistics
import time
from pathlib import Path

import nlmegls

DATA = Path(__file__).resolve().parent / "data" / "dqrdc2-cases.txt"


def load_cases():
    cases = []
    for line in DATA.read_text().splitlines():
        parts = line.split()
        n, p = int(parts[0]), int(parts[1])
        xy = [float(v) for v in parts[2:]]
        cases.append((xy, n, p))
    return cases


def one(cases):
    return [nlmegls.gls_loglik(xy, n, p, 0, 0.0, 0.0, 0.0)[1] for xy, n, p in cases]


cases = load_cases()
value = one(cases)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(cases)
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(v) for v in value), statistics.median(elapsed))
)
