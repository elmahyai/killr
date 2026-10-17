import statistics
import time

def one():
    from tools.paths import file_path_as_absolute
    ok = file_path_as_absolute("/tmp")
    try:
        file_path_as_absolute("no-such-assertthat-path")
        bad = "NOERROR"
    except ValueError as error:
        bad = str(error)
    try:
        file_path_as_absolute(["a", "b"])
        two = "NOERROR"
    except ValueError as error:
        two = str(error)
    return ok + "\n" + bad + "\n" + two + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
