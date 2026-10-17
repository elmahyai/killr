import json
import statistics
import time

from glue import (
    Id,
    SQL,
    as_glue,
    backtick,
    double_quote,
    glue,
    glue_col,
    glue_collapse,
    glue_data,
    glue_data_col,
    glue_data_safe,
    glue_data_sql,
    glue_safe,
    glue_sql,
    glue_sql_collapse,
    identity_transformer,
    single_quote,
    sqlite,
    trim,
)
from glue.interpolate import plain

def one():
    return glue_data_sql({"name": "O'Malley"}, "INSERT {name}", con=sqlite, envir={})

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

shown = plain(value) if not isinstance(value, (int, float, str)) else value
print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
