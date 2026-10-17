import gzip
import io
import math
from pathlib import Path

from jsonlite import (
    NA,
    DataFrame,
    I,
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


def test_base64_round_trip():
    assert base64_enc(b"hello") == "aGVsbG8="
    assert base64_dec("aGVsbG8=") == b"hello"
    assert base64url_enc(b"hello") == "aGVsbG8"
    assert base64url_dec("aGVsbG8") == b"hello"


def test_validate_prettify_and_minify():
    assert validate('{"a":1}') is True
    assert validate("{") is False
    assert prettify("[1,2]", indent=2) == "[\n  1,\n  2\n]\n"
    assert minify("[\n  1,\n  2\n]") == "[1,2]"


def test_tojson_matches_the_probed_mapping():
    assert toJSON([1, 2, 3]) == "[1,2,3]"
    assert toJSON([1.2, 1.23456, math.pi]) == "[1.2,1.2346,3.1416]"
    assert toJSON(math.pi, digits=3) == "[3.142]"
    assert toJSON(math.pi, digits=I(3)) == "[3.14]"
    assert toJSON([1, NA]) == '[1,"NA"]'
    assert toJSON([float("nan"), float("inf"), float("-inf")]) == '["NaN","Inf","-Inf"]'
    assert toJSON(["a", 'b"c', NA]) == '["a","b\\"c",null]'
    assert toJSON([True, False, NA]) == "[true,false,null]"
    assert toJSON({"a": 1, "b": "x", "c": None}) == '{"a":[1],"b":["x"],"c":{}}'
    assert toJSON({"foo": unbox(123)}) == '{"foo":123}'
    frame = DataFrame({"a": [1, 2], "b": ["x", "y"]})
    assert toJSON(frame) == '[{"a":1,"b":"x"},{"a":2,"b":"y"}]'
    assert toJSON(DataFrame({"a": [1, NA], "b": ["x", "y"]})) == '[{"a":1,"b":"x"},{"b":"y"}]'
    assert toJSON([]) == "[]"
    assert toJSON(None) == "{}"


def test_fromjson_and_parse_json():
    frame = fromJSON('[{"a":1,"b":"x"},{"a":2,"b":"y"}]')
    assert frame.columns == {"a": [1, 2], "b": ["x", "y"]}
    parsed = parse_json('[{"a":1,"b":"x"}]')
    assert parsed[0]["b"] == "x"


def test_gzip_round_trip_uses_the_json_text():
    raw = as_gzjson_raw({"a": 1})
    assert gzip.decompress(raw).decode() == '{"a":[1]}'
    assert parse_gzjson_raw(raw) == {"a": [1]}
    assert parse_gzjson_b64(as_gzjson_b64({"a": 1})) == {"a": [1]}


def test_read_write_and_stream(tmp_path: Path):
    path = tmp_path / "obj.json"
    write_json({"a": 1}, path)
    assert path.read_text() == '{"a":[1]}\n'
    assert read_json(path) == {"a": [1]}
    frame = DataFrame({"a": [1, 2], "b": ["x", "y"]})
    buf = io.StringIO()
    stream_out(frame, buf)
    assert buf.getvalue() == '{"a":1,"b":"x"}\n{"a":2,"b":"y"}\n'
    bound = stream_in(io.StringIO(buf.getvalue()))
    assert bound.columns == {"a": [1, 2], "b": ["x", "y"]}


def test_flatten_and_rbind():
    vehicle = DataFrame({"model": ["Piranha Prowler", "Royal Racer"]})
    vehicle.columns["stats"] = DataFrame({"speed": [55, 34], "weight": [67, 24]})
    frame = DataFrame(
        {
            "driver": ["Bowser", "Peach"],
            "occupation": ["Koopa", "Princess"],
            "vehicle": vehicle,
        }
    )
    flat = flatten(frame)
    assert list(flat.columns) == [
        "driver",
        "occupation",
        "vehicle.model",
        "vehicle.stats.speed",
        "vehicle.stats.weight",
    ]
    once = flatten(frame, recursive=False)
    assert list(once.columns) == ["driver", "occupation", "vehicle.model", "vehicle.stats"]
    bound = rbind_pages(
        [
            DataFrame({"foo": [1, 2], "bar": [True, False]}),
            DataFrame({"foo": [3], "col": ["blue"]}),
        ]
    )
    assert bound.columns["foo"] == [1, 2, 3]
    assert bound.columns["bar"] == [True, False, NA]
    assert bound.columns["col"] == [NA, NA, "blue"]


def test_serialize_round_trip():
    text = serializeJSON({"a": 1, "b": "x"})
    assert text == (
        '{"type":"list","attributes":{"names":{"type":"character","attributes":{},"value":["a","b"]}},'
        '"value":[{"type":"integer","attributes":{},"value":[1]},{"type":"character","attributes":{},"value":["x"]}]}'
    )
    assert unserializeJSON(text) == {"a": 1, "b": "x"}
