import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from nlme_pdsymm import matrix_log_pd

# Same cases as pdsymm-log-r.R: 12 cases from one LCG stream, the first 8 random
# positive definite and the last 4 near-singular (shift on the (1,1) half-log entry).
CASE_ORDERS = [2, 3, 4, 5, 6, 3, 4, 2, 3, 4, 5, 6]
SHIFTS = [0, 0, 0, 0, 0, 0, 0, 0, 4, 6, 8, 10]
MULTIPLIER = 1664525
INCREMENT = 1013904223
MODULUS = 4294967296


class Lcg:
    def __init__(self, state: int) -> None:
        self.state = state

    def uniform(self) -> float:
        self.state = (MULTIPLIER * self.state + INCREMENT) % MODULUS
        return self.state / MODULUS


def build_cases():
    rng = Lcg(12345)
    cases = []
    for q, shift in zip(CASE_ORDERS, SHIFTS):
        n_par = q * (q + 1) // 2
        params = [(2.0 * rng.uniform() - 1.0) * 0.7 for _ in range(n_par)]
        params[0] = params[0] - shift
        cases.append((q, params))
    return cases


def one(cases):
    out = []
    for q, params in cases:
        factor = np.asarray(matrix_log_pd(params, q), dtype=np.float64).reshape(q, q, order="F")
        value = factor.T @ factor
        out.extend(factor.reshape(-1, order="F").tolist())
        out.extend(value.reshape(-1, order="F").tolist())
    return out


cases = build_cases()
value = one(cases)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(cases)
    elapsed.append((time.perf_counter() - started) * 1000)
print('{"value":[%s],"median_ms":%.17g}' % (",".join("%.17g" % v for v in value), statistics.median(elapsed)))
