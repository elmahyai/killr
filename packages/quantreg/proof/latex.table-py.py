import statistics
import time
import numpy as np
from quantreg.latex import latex_table

x = np.array([[1.2, 2.3], [3.4, 4.5]], dtype=object)
text = latex_table(x, file="/tmp/qtable", rowlabel="rows", caption="Demo",
                   _call='latex.table(x = x, file = "/tmp/qtable", rowlabel = "rows", caption = "Demo")')
def one():
    return latex_table(x, file="/tmp/qtable", rowlabel="rows", caption="Demo",
                       _call='latex.table(x = x, file = "/tmp/qtable", rowlabel = "rows", caption = "Demo")')
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(one(), end="")
print(f"\n{statistics.median(elapsed):.17g}")
