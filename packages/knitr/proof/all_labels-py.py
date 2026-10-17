import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/knitr")
from knitr.all_labels import all_labels, chunk, knit_code

knit_code.restore()
knit_code.enclosure.clear()
knit_code.set(
    a=chunk("x", engine="R", echo=True, results="markup"),
    b=chunk("y", engine="Rcpp", echo=False, results="markup"),
    c=chunk("z", engine="R", echo=False, results="hide"),
)


def one():
    return all_labels("echo == FALSE", 'results != "hide"')


value = one()
text = (
    'all_labels(echo == FALSE, results != "hide") returns '
    + ", ".join(value)
    + ".\n"
)
with open(
    "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/all_labels-python.txt",
    "w",
    encoding="utf-8",
) as handle:
    handle.write(text)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
