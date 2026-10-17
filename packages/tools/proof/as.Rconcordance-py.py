import statistics
import time

def one():
    from tools.concordance import as_rconcordance
    a = as_rconcordance(1)
    b = as_rconcordance("concordance:foo.tex:bar.Rnw:5 1 1")
    c = as_rconcordance("stuff concordance:foo.tex:bar.Rnw:ofs 2:10 1 2 3 4")
    return (
        f"A {'TRUE' if a is None else 'FALSE'}\n"
        f"B {b['offset']} {b['srcFile']} {','.join(str(v) for v in b['srcLine'])}\n"
        f"C {c['offset']} {c['srcFile']} {','.join(str(v) for v in c['srcLine'])}\n"
    )

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
