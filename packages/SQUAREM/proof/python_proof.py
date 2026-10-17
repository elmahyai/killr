import time
import numpy as np
from SQUAREM import squarem, fpiter


def fixed(x, target, rate):
    return target + rate * (x - target)


def objective(x, target, rate):
    return float(np.sum((x - target) ** 2))


x = np.array([3., -2., 5.])
target = np.array([1., 2., 3.])
cases = {
    "squarem": lambda: squarem(x, fixed, objective, target=target, rate=.92,
                               control={"tol": 1e-10, "maxiter": 500, "method": 3}),
    "fpiter": lambda: fpiter(x, fixed, objective, target=target, rate=.92,
                             control={"tol": 1e-10, "maxiter": 500}),
}
for name, call in cases.items():
    call()
    times = []
    for _ in range(20):
        start = time.perf_counter()
        result = call()
        times.append(time.perf_counter() - start)
    print(name, ",".join(format(v, ".17g") for v in result["par"]),
          result["fpevals"], result["objfevals"], format(result["value.objfn"], ".17g"),
          np.median(times) * 1000)
