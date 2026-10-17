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
    import gzip
    return gzip.decompress(as_gzjson_raw({"a": 1})).decode()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
