import contextlib
import io
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.print_mclustda import print_MclustDA


def make_mclust_da():
    return {
        "models": {
            "setosa": {"n": 50, "modelName": "EEE", "G": 2},
            "versicolor": {"n": 50, "modelName": "XXX", "G": 1},
            "virginica": {"n": 50, "modelName": "XXX", "G": 1},
        },
        "type": "MclustDA",
        "n": 150,
        "d": 4,
    }


def one():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        print_MclustDA(make_mclust_da())
    return output.getvalue().splitlines()


value = one()
print("\n".join(value))
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("%.17g" % statistics.median(elapsed))
