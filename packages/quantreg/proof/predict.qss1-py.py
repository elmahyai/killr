import statistics
import time
import numpy as np
from quantreg.rqss import predict_qss1

object = {"xyz": np.column_stack(([0, 1, 2, 4], [2, 3, 1, 5]))}
newdata = np.array([[0], [.25], [1], [1.5], [3], [4]])

def one():
    value = predict_qss1(object, newdata)
    return np.concatenate([value["x"], value["y"], value["D"].toarray().reshape(-1)])

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
print(",".join(f"{item:.17g}" for item in value))
print(f"{statistics.median(elapsed):.17g}")
