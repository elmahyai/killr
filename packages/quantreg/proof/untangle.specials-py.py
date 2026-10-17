import statistics
import time
import numpy as np
from quantreg.auxiliary import terms_additive, untangle_specials
formulas = [
    "y ~ x1 + qss(x2) + x3 + qss(x4)",
    "y ~ qss(x1) * x2",
    "y ~ qss(x1) / (x2 + x3)",
    "y ~ (x1 + qss(x2))^2",
    "y ~ qss(qss(x1)) + x2:x3",
]
tts = [terms_additive(formula, specials=["qss"]) for formula in formulas]

def one():
    values = []
    for tt in tts:
        a = untangle_specials(tt, "qss")
        b = untangle_specials(tt, "qss", order=2)
        values.extend([
            ",".join(tt.variables),
            ",".join(str(i) for i in tt.specials["qss"]),
            ",".join(a["vars"]),
            ",".join(str(i) for i in a["terms"]),
            ",".join(str(i) for i in b["terms"]),
        ])
    return values
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
print("|".join(value))
print(f'{statistics.median(elapsed):.17g}')
