
import json, statistics, time, os, tempfile, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from haven import (
    as_factor, format_tagged_na, is_labelled, is_tagged_na, labelled, labelled_spss,
    na_tag, print_labels, print_tagged_na, read_dta, read_por, read_sas, read_sav,
    read_spss, read_stata, read_xpt, tagged_na, vec_arith_haven_labelled,
    write_dta, write_sas, write_sav, write_xpt, zap_empty, zap_formats, zap_label,
    zap_labels, zap_missing, zap_widths,
)
from haven.labelled import Vector, is_missing
from tibble import new_tibble

def one():
    from haven.tagged import is_na_double
    x = labelled_spss([1, 2, 9], {"a": 1}, na_values=[9])
    z = zap_missing(x)
    vals = ["NA" if is_na_double(v) else str(int(v)) for v in z.values]
    return vals + ["TRUE" if "haven_labelled_spss" in z.class_ else "FALSE", "TRUE" if "haven_labelled" in z.class_ else "FALSE"]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
