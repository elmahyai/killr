import json
import statistics
import time

from jsonlite import (
    NA,
    DataFrame,
    as_gzjson_b64,
    as_gzjson_raw,
    base64_dec,
    base64_enc,
    base64url_dec,
    base64url_enc,
    flatten,
    fromJSON,
    minify,
    parse_gzjson_b64,
    parse_gzjson_raw,
    parse_json,
    prettify,
    rbind_pages,
    read_json,
    serializeJSON,
    stream_in,
    stream_out,
    toJSON,
    unbox,
    unserializeJSON,
    validate,
    write_json,
)
def one():
    bound = rbind_pages([DataFrame({"foo": [1, 2], "bar": [True, False]}), DataFrame({"foo": [3], "col": ["blue"]})])
    def cell(value):
        if value is NA:
            return "NA"
        if value is True:
            return "TRUE"
        if value is False:
            return "FALSE"
        return str(value)
    rows = zip(bound.columns["foo"], bound.columns["bar"], bound.columns["col"])
    return "|".join(":".join(cell(item) for item in row) for row in rows)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
