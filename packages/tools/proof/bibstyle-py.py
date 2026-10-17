import statistics
import time


def one():
    from tools.bibstyle import bibstyle, get_bibstyle

    parts = []
    jss = bibstyle()
    parts.append(",".join(sorted(jss.keys(), key=str.lower)))
    bibstyle(
        "unsorted",
        sortKeys=lambda refs: list(range(1, len(refs) + 1)),
        fmtPrefix=lambda paper: f"[{paper['.index']}]",
        _init=True,
        _default=False,
    )
    uns = bibstyle("unsorted", _default=False)
    sk = uns["sortKeys"]([{}, {}])
    parts.append(",".join(str(x) for x in sk))
    parts.append(uns["fmtPrefix"]({".index": 3}))
    parts.append(get_bibstyle())
    return "\n".join(parts) + "\n"


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
