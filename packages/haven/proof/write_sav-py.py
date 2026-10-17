
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
    tmp = tempfile.NamedTemporaryFile(suffix=".sav", delete=False)
    tmp.close()
    x = labelled_spss([1, 9, 11], {"Good": 1}, na_values=[9], na_range=[10, 12], label="q")
    write_sav(new_tibble([x], nrow=3, names=["q"]), tmp.name)
    col = read_sav(tmp.name, user_na=True).columns[0]
    os.unlink(tmp.name)
    return [str(int(v)) for v in col.values] + [str(int(v)) for v in col.na_values] + [str(int(v)) for v in col.na_range] + [col.label]
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
