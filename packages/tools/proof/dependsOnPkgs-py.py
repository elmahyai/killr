import statistics
import time

def one():
    from tools.deps import depends_on_pkgs
    rows = [
        {"Package": "a", "Depends": "b, R (>= 4.0)", "Imports": None, "LinkingTo": None, "Suggests": "c", "Enhances": None},
        {"Package": "b", "Depends": None, "Imports": "c", "LinkingTo": None, "Suggests": None, "Enhances": None},
        {"Package": "c", "Depends": None, "Imports": None, "LinkingTo": None, "Suggests": None, "Enhances": None},
        {"Package": "d", "Depends": "a", "Imports": None, "LinkingTo": None, "Suggests": None, "Enhances": None},
    ]
    def show(value):
        return ",".join(value)
    return "\n".join([
        show(depends_on_pkgs("c", installed=rows)),
        show(depends_on_pkgs("c", dependencies="most", installed=rows)),
        show(depends_on_pkgs("c", dependencies="all", recursive=False, installed=rows)),
        show(depends_on_pkgs("b", recursive=False, installed=rows)),
    ]) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
