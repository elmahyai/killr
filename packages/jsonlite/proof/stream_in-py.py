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
    import io
    frame = stream_in(io.StringIO('{"a":1,"b":"x"}\n{"a":2,"b":"y"}\n'))
    return "|".join(f"{a} {b}" for a, b in zip(frame.columns["a"], frame.columns["b"]))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
