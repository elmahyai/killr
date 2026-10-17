import os
import statistics
import time

from utils.file_test import file_test


def one():
    r_home = os.environ.get("R_HOME", "/usr/lib/R")
    directory = os.path.join(r_home, "library", "stats")
    return ",".join(
        [
            str(int(file_test("-d", directory))),
            str(
                int(
                    file_test(
                        "-nt",
                        os.path.join(directory, "R"),
                        os.path.join(directory, "demo"),
                    )
                )
            ),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
