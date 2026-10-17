import statistics
import time

def one():
    from tools.deps import package_dependencies
    db = [
        {"Package": "a", "Depends": "b, c", "Imports": "d", "LinkingTo": None, "Suggests": None, "Enhances": None},
        {"Package": "b", "Depends": None, "Imports": "a", "LinkingTo": None, "Suggests": None, "Enhances": None},
        {"Package": "c", "Depends": None, "Imports": None, "LinkingTo": None, "Suggests": None, "Enhances": None},
    ]
    db2 = [
        {"Package": "a", "Depends": "b", "Imports": None, "LinkingTo": None, "Suggests": None, "Enhances": None},
        {"Package": "b", "Depends": "c", "Imports": None, "LinkingTo": None, "Suggests": None, "Enhances": None},
        {"Package": "c", "Depends": None, "Imports": None, "LinkingTo": None, "Suggests": None, "Enhances": None},
    ]
    def fmt(value):
        return " ".join(f"{key}:{','.join(names)}" for key, names in value.items())
    return "\n".join([
        fmt(package_dependencies(["a", "b"], db=db)),
        fmt(package_dependencies("a", db=db, recursive=True)),
        fmt(package_dependencies("a", db=db, reverse=True)),
        fmt(package_dependencies("a", db=db2, recursive=True)),
        fmt(package_dependencies("c", db=db2, reverse=True, recursive=True)),
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
