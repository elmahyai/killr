import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/knitr")
from knitr.asis_output import asis_output


def one():
    return asis_output("hello", meta={"id": "fig1"}, cacheable=False)


value = one()
cache = value.attr("knit_cacheable")
if cache is True:
    cache_word = "TRUE"
    cache_json = True
elif cache is False:
    cache_word = "FALSE"
    cache_json = False
else:
    cache_word = "NA"
    cache_json = None
cls = value.attr("class")
class_list = [cls] if isinstance(cls, str) else list(cls)
text = (
    'asis_output("hello", meta = list(id = "fig1"), cacheable = FALSE) returns '
    + value.value
    + " with class "
    + " ".join(class_list)
    + ", meta id "
    + value.attr("knit_meta")["id"]
    + ", and cacheable "
    + cache_word
    + ".\n"
)
with open(
    "/home/ahmed/killr_projects/killr/packages/knitr/docs/output/asis_output-python.txt",
    "w",
    encoding="utf-8",
) as handle:
    handle.write(text)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
payload = {
    "typeof": "character" if isinstance(value.value, str) else type(value.value).__name__,
    "value": value.value,
    "attributes": [name for name, _ in value.attrs],
    "class": class_list,
    "knit_meta": value.attr("knit_meta"),
    "knit_cacheable": cache_json,
}
print(json.dumps({"value": payload, "median_ms": statistics.median(elapsed)}))
