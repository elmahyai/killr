import statistics
import time

PKG = "/home/ahmed/killr_projects/killr/packages/tools/proof/checkTnF_pkg"


def one():
    from tools.check_tnf import check_tnf

    res = check_tnf(dir=PKG)
    lines = []
    for path in res:
        lines.append(path)
        lines.extend(res[path])
    return "\n".join(lines) + "\n"


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
