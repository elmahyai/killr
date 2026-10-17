"""Python translation of the R package jsonlite."""

from jsonlite._base64 import base64_dec, base64_enc, base64url_dec, base64url_enc
from jsonlite._decode import fromJSON, parse_json
from jsonlite._encode import toJSON, unbox
from jsonlite._format import minify, prettify, validate
from jsonlite._frames import flatten, rbind_pages
from jsonlite._gzip import as_gzjson_b64, as_gzjson_raw, parse_gzjson_b64, parse_gzjson_raw
from jsonlite._io import read_json, stream_in, stream_out, write_json
from jsonlite._serialize import serializeJSON, unserializeJSON
from jsonlite._values import NA, DataFrame, I

__all__ = [
    "DataFrame",
    "I",
    "NA",
    "as_gzjson_b64",
    "as_gzjson_raw",
    "base64_dec",
    "base64_enc",
    "base64url_dec",
    "base64url_enc",
    "flatten",
    "fromJSON",
    "minify",
    "parse_gzjson_b64",
    "parse_gzjson_raw",
    "parse_json",
    "prettify",
    "rbind_pages",
    "read_json",
    "serializeJSON",
    "stream_in",
    "stream_out",
    "toJSON",
    "unbox",
    "unserializeJSON",
    "validate",
    "write_json",
]
