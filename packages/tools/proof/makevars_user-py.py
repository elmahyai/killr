import statistics
import time

def one():
    import os, tempfile
    from tools.session import makevars_user
    path = tempfile.mktemp()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("X=1\n")
    os.environ["R_MAKEVARS_USER"] = path
    hit = makevars_user()
    os.environ["R_MAKEVARS_USER"] = tempfile.mktemp()
    miss = "<none>" if makevars_user() == "" else "BAD"
    shown = "HIT" if hit == path else hit
    return shown + "\n" + miss + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
