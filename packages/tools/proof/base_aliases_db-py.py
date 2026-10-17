import statistics
import time


def summarize(db):
    parts = []
    for pkg in db:
        inner = db[pkg]
        rd_parts = []
        for rd in inner:
            rd_parts.append("\1".join(inner[rd]))
        parts.append("\2".join(rd_parts))
    return "\3".join(parts)


def one():
    from tools.base_aliases_db import base_aliases_db

    db = base_aliases_db(verbose=False, ncpus=1)
    n_pkgs = len(db)
    n_rd = sum(len(inner) for inner in db.values())
    n_alias = sum(len(aliases) for inner in db.values() for aliases in inner.values())
    body = summarize(db)
    return f"{n_pkgs}\n{n_rd}\n{n_alias}\n{len(body)}\n{body}\n"


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
