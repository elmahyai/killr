"""fromJSON and isValidJSON.

The default reader follows libjson: comments are allowed, an empty array
slot is null, and every number is a double. A handler follows the older
token parser, which keeps whole numbers as integers.
"""

from __future__ import annotations

import json
import os
import re

from rjsonio.errors import RJSONIOError
from rjsonio.values import NA, AsIs, Atomic, RList

JSON_T_NONE = 0
JSON_T_ARRAY_BEGIN = 1
JSON_T_ARRAY_END = 2
JSON_T_OBJECT_BEGIN = 3
JSON_T_OBJECT_END = 4
JSON_T_INTEGER = 5
JSON_T_FLOAT = 6
JSON_T_NULL = 7
JSON_T_TRUE = 8
JSON_T_FALSE = 9
JSON_T_STRING = 10
JSON_T_KEY = 11
JSON_T_MAX = 12

StrictLogical = 2
StrictNumeric = 4
StrictCharacter = 8
Strict = StrictNumeric + StrictCharacter + StrictLogical

_NONE = 0
_ALL = 1
_CONTENT = re.compile(r"^[\s]*[\[{]")


class JSONParserHandler:
    def __init__(self, update, value):
        self.update = update
        self.value = value

    def __call__(self, *args, **kwargs):
        return self.update(*args, **kwargs)


def basicJSONHandler(default_size: int = 100, simplify: bool = False) -> JSONParserHandler:
    """Collect parser events into a list, the way basicJSONHandler does."""
    stack = []
    current = None
    keys: list[str] = []
    lengths = [0]

    def extend():
        nonlocal current
        if current is None:
            current = []
        lengths[0] += 1
        while len(current) < lengths[0]:
            current.extend([None] * max(len(current), 8))

    def update(type_code, val=None):
        nonlocal current, keys
        if type_code == JSON_T_KEY:
            keys.insert(0, val)
        elif type_code in (JSON_T_ARRAY_BEGIN, JSON_T_OBJECT_BEGIN):
            stack.append(current)
            current = [None] * default_size
            lengths.insert(0, 0)
        elif type_code in (JSON_T_ARRAY_END, JSON_T_OBJECT_END):
            count = lengths.pop(0)
            tmp = current[:count]
            if type_code == JSON_T_ARRAY_END and simplify:
                obj = condense(tmp)
            else:
                obj = tmp
            if type_code == JSON_T_OBJECT_END:
                used = keys[: len(obj)]
                obj = RList(obj, list(reversed(used)))
                del keys[: len(used)]
            current = stack.pop()
            extend()
            current[lengths[0] - 1] = obj
        elif JSON_T_OBJECT_END < type_code < JSON_T_KEY:
            if current is None:
                current = []
            extend()
            current[lengths[0] - 1] = val
        return True

    def get_value(simplify_top: bool = True):
        if current is None:
            return None
        filled = current[: lengths[0]]
        if simplify_top and len(filled) == 1:
            return filled[0]
        return filled

    return JSONParserHandler(update, get_value)


def condense(val, strict: bool = False):
    if isinstance(val, RList) and val.names:
        return val
    items = list(val)
    if any(_has_names(item) for item in items):
        return val
    lengths = [_length(item) for item in items]
    if lengths and all(length == 1 for length in lengths):
        if not all(_is_atomic_scalar(item) for item in items):
            return val
        return _unlist(items)
    flat = _unlist(items)
    if flat is None or (isinstance(flat, list) and len(flat) == 0):
        return None
    kinds = [_atomic_kind(item) for item in items]
    same_length = lengths and all(length == lengths[0] for length in lengths)
    if not same_length:
        return val
    if strict:
        uniform = all(kind == kinds[0] for kind in kinds)
    else:
        uniform = not any(kind == "character" for kind in kinds) or all(
            kind == "character" for kind in kinds
        )
    if uniform and lengths[0]:
        from rjsonio.values import Matrix

        rows = [_as_list(item) for item in items]
        data = []
        for column in range(lengths[0]):
            for row in rows:
                data.append(row[column])
        if all(item == "integer" for item in kinds):
            kind = "integer"
        elif all(item == "logical" for item in kinds):
            kind = "logical"
        elif all(item == "character" for item in kinds):
            kind = "character"
        else:
            kind = "numeric"
            data = [None if value is None else float(value) for value in data]
        return Matrix(data, len(items), lengths[0], kind)
    return val


def _has_names(item) -> bool:
    if isinstance(item, (Atomic, RList)):
        return bool(item.names)
    return isinstance(item, dict) and len(item) > 0


def _length(item) -> int:
    if isinstance(item, (Atomic, RList, list, str)):
        return len(item)
    if item is None:
        return 0
    return 1


def _is_atomic_scalar(item) -> bool:
    if isinstance(item, Atomic):
        return len(item) == 1
    return isinstance(item, (bool, int, float, str)) or item is None


def _atomic_kind(item) -> str:
    if isinstance(item, Atomic):
        return item.kind
    if isinstance(item, bool):
        return "logical"
    if isinstance(item, int):
        return "integer"
    if isinstance(item, str):
        return "character"
    if isinstance(item, float):
        return "numeric"
    if isinstance(item, list) and item:
        kinds = {_atomic_kind(part) for part in item}
        if kinds == {"integer"}:
            return "integer"
        if kinds == {"logical"}:
            return "logical"
        if kinds == {"character"}:
            return "character"
        if kinds <= {"integer", "numeric"}:
            return "numeric"
    return "numeric"


def _as_list(item):
    if isinstance(item, Atomic):
        return item.values
    if isinstance(item, list):
        return item
    return [item]


def _unlist(items):
    values = []
    kind = None
    for item in items:
        if isinstance(item, Atomic):
            values.extend(item.values)
            kind = item.kind
        elif isinstance(item, bool):
            values.append(item)
            kind = "logical"
        elif isinstance(item, int):
            values.append(item)
            kind = "numeric" if kind not in (None, "integer") else "integer"
        elif isinstance(item, float):
            values.append(item)
            kind = "numeric"
        elif isinstance(item, str):
            values.append(item)
            kind = "character"
        elif item is None:
            values.append(None)
        else:
            return items
    if kind == "logical" and all(isinstance(value, (bool, type(None))) for value in values):
        return Atomic("logical", values)
    if kind == "character":
        return Atomic("character", values)
    if kind == "integer" and all(
        value is None or (isinstance(value, int) and not isinstance(value, bool)) for value in values
    ):
        return Atomic("integer", values)
    if all(not isinstance(value, str) for value in values):
        return Atomic("numeric", [None if value is None else float(value) for value in values])
    return Atomic("character", ["" if value is None else str(value) for value in values])


def _strip_comments(text: str) -> str:
    out = []
    index = 0
    size = len(text)
    in_string = False
    escaped = False
    while index < size:
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if text.startswith("//", index):
            index += 2
            while index < size and text[index] != "\n":
                index += 1
            out.append(" ")
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise RJSONIOError("invalid JSON input")
            index = end + 2
            out.append(" ")
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _copy_string(text: str, index: int) -> tuple[str, int]:
    start = index
    index += 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return text[start : index + 1], index + 1
        index += 1
    raise RJSONIOError("invalid JSON input")


def _copy_literal(text: str, index: int) -> tuple[str, int]:
    start = index
    while index < len(text) and text[index] not in " \t\r\n,]}":
        index += 1
    return text[start:index], index


def _insert_nulls(text: str) -> str:
    out = []
    index = 0
    size = len(text)
    stack = []
    in_string = False
    escaped = False
    while index < size:
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char in " \t\r\n":
            out.append(char)
            index += 1
            continue
        frame = stack[-1] if stack else None
        if char == "[":
            stack.append({"kind": "array", "expect": "value", "count": 0})
            out.append(char)
            index += 1
            continue
        if char == "{":
            stack.append({"kind": "object", "expect": "key", "count": 0})
            out.append(char)
            index += 1
            continue
        if char == "]":
            if frame is None or frame["kind"] != "array":
                raise RJSONIOError("invalid JSON input")
            if frame["expect"] == "value" and frame["count"] > 0:
                out.append("null")
            stack.pop()
            out.append(char)
            if stack:
                stack[-1]["expect"] = "sep"
                stack[-1]["count"] += 1
            index += 1
            continue
        if char == "}":
            if frame is None or frame["kind"] != "object":
                raise RJSONIOError("invalid JSON input")
            if frame["expect"] == "value":
                out.append("null")
            elif frame["expect"] == "key" and frame["count"] > 0:
                raise RJSONIOError("Invalid JSON Node")
            stack.pop()
            out.append(char)
            if stack:
                stack[-1]["expect"] = "sep"
                stack[-1]["count"] += 1
            index += 1
            continue
        if char == ",":
            if frame is None:
                raise RJSONIOError("invalid JSON input")
            if frame["kind"] == "array" and frame["expect"] == "value":
                out.append("null")
                frame["count"] += 1
            elif frame["kind"] == "object" and frame["expect"] == "value":
                out.append("null")
                frame["count"] += 1
                frame["expect"] = "key"
                out.append(char)
                index += 1
                continue
            elif frame["expect"] != "sep":
                raise RJSONIOError("invalid JSON input")
            frame["expect"] = "value" if frame["kind"] == "array" else "key"
            out.append(char)
            index += 1
            continue
        if char == ":":
            if frame is None or frame["expect"] != "colon":
                raise RJSONIOError("invalid JSON input")
            frame["expect"] = "value"
            out.append(char)
            index += 1
            continue
        if frame is None:
            raise RJSONIOError("invalid JSON input")
        if frame["kind"] == "object" and frame["expect"] == "key":
            if char != '"':
                raise RJSONIOError("invalid JSON input")
            token, index = _copy_string(text, index)
            out.append(token)
            frame["expect"] = "colon"
            continue
        if char == '"':
            token, index = _copy_string(text, index)
        else:
            token, index = _copy_literal(text, index)
            if token not in ("true", "false", "null") and not _is_number(token):
                raise RJSONIOError("invalid JSON input")
        out.append(token)
        frame["expect"] = "sep"
        frame["count"] += 1
    if stack:
        raise RJSONIOError("invalid JSON input")
    return "".join(out)


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _loads(text: str):
    stripped = _strip_comments(text)
    if not _CONTENT.match(stripped or ""):
        raise RJSONIOError("invalid JSON input")
    normalized = _insert_nulls(stripped)
    try:
        return json.loads(normalized, parse_int=int, parse_float=float)
    except json.JSONDecodeError as exc:
        raise RJSONIOError("invalid JSON input") from exc


def _is_logical_na(null_value) -> bool:
    return null_value is NA


def _simplify_node(node, simplify: int, null_value, simplify_with_names: bool):
    if isinstance(node, dict):
        names = list(node.keys())
        elements = [
            _simplify_node(node[name], simplify, null_value, simplify_with_names)
            for name in names
        ]
        parent = "object"
    elif isinstance(node, list):
        names = None
        elements = [
            _simplify_node(item, simplify, null_value, simplify_with_names) for item in node
        ]
        parent = "array"
    else:
        return _scalar(node)

    if len(elements) == 0:
        if parent == "object":
            return RList([], [])
        return AsIs(RList([], None))

    numbers = strings = logicals = nulls = 0
    for element in elements:
        if element is None:
            nulls += 1
        elif isinstance(element, bool):
            logicals += 1
        elif isinstance(element, str):
            strings += 1
        elif isinstance(element, (int, float)) and not isinstance(element, bool):
            numbers += 1
    size = len(elements)
    all_same = numbers == size or strings == size or logicals == size
    if _is_logical_na(null_value):
        all_same = all_same or (
            numbers + nulls == size or strings + nulls == size or logicals + nulls == size
        )
    can_simplify = simplify_with_names or not names
    if can_simplify and simplify != _NONE and all_same:
        bit_ok = (
            (numbers == size and simplify & StrictNumeric)
            or (logicals == size and simplify & StrictLogical)
            or (strings == size and simplify & StrictCharacter)
            or simplify == Strict
            or (simplify == _ALL)
        )
        if bit_ok or simplify == _ALL:
            kind = "character" if strings else "numeric" if numbers or (nulls and numbers + nulls == size) else "logical"
            if strings == 0 and numbers == 0 and logicals == 0 and nulls:
                kind = "logical" if _is_logical_na(null_value) else "numeric"
            values = [_coerce(element, kind, null_value) for element in elements]
            return Atomic(kind, values, names)
    if names is None:
        return elements
    return RList(elements, names)


def _scalar(node):
    if isinstance(node, bool) or node is None or isinstance(node, str):
        return node
    if isinstance(node, int):
        return float(node)
    return float(node)


def _coerce(element, kind: str, null_value):
    if element is None:
        if kind == "numeric":
            return float("nan")
        if kind == "logical":
            return None
        return None
    if isinstance(element, Atomic):
        element = element.values[0]
    if kind == "numeric":
        if element is None or (isinstance(element, float) and element != element):
            return float("nan")
        if isinstance(element, bool):
            return float(element)
        return float(element)
    if kind == "logical":
        if isinstance(element, bool):
            return element
        return None
    if element is None:
        return None
    return str(element)


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError as exc:
        raise RJSONIOError("invalid JSON input") from exc
    return "\n".join(lines)


def _as_text(content: str, as_text) -> bool:
    if as_text is not None:
        return bool(as_text)
    if os.path.exists(content):
        return False
    return _CONTENT.match(content) is not None


def fromJSON(
    content,
    handler=None,
    default_size: int = 100,
    depth: int = 150,
    allow_comments: bool = True,
    as_text=None,
    data=None,
    max_char=None,
    simplify: int = Strict,
    null_value=None,
    simplify_with_names: bool = True,
    encoding=None,
    string_fun=None,
):
    """Read JSON text or a file path."""
    del default_size, data, max_char, encoding
    if isinstance(content, AsIs):
        content = content.value
        as_text = True
    if not isinstance(content, str):
        raise RJSONIOError("fromJSON() content must be a string or a file path.")
    if not _as_text(content, as_text):
        content = _read_text(content)
    if string_fun is not None and not callable(string_fun):
        raise RJSONIOError("stringFun needs to be a function or identify a native routine")
    # libjson parses comments even when allowComments is FALSE.
    del allow_comments
    if isinstance(handler, JSONParserHandler):
        tree = _loads(content)
        _check_depth(tree, depth)
        _emit(tree, handler.update, string_fun, ints=True)
        return handler.value()
    if callable(handler):
        tree = _loads(content)
        _check_depth(tree, depth)
        _emit(tree, handler, string_fun, ints=True)
        return None
    tree = _loads(content)
    _check_depth(tree, depth)
    if string_fun is not None:
        tree = _map_strings(tree, string_fun)
    return _simplify_node(tree, int(simplify), null_value, bool(simplify_with_names))


def _check_depth(node, depth: int, level: int = 1) -> None:
    if level > depth:
        raise RJSONIOError("invalid JSON input")
    if isinstance(node, dict):
        for value in node.values():
            _check_depth(value, depth, level + 1)
    elif isinstance(node, list):
        for value in node:
            _check_depth(value, depth, level + 1)


def _map_strings(node, string_fun):
    if isinstance(node, str):
        return string_fun(node)
    if isinstance(node, dict):
        return {key: _map_strings(value, string_fun) for key, value in node.items()}
    if isinstance(node, list):
        return [_map_strings(value, string_fun) for value in node]
    return node


def _emit(node, update, string_fun, ints: bool) -> None:
    if isinstance(node, dict):
        update(JSON_T_OBJECT_BEGIN, None)
        for key, value in node.items():
            update(JSON_T_KEY, key)
            _emit(value, update, string_fun, ints)
        update(JSON_T_OBJECT_END, None)
        return
    if isinstance(node, list):
        update(JSON_T_ARRAY_BEGIN, None)
        for value in node:
            _emit(value, update, string_fun, ints)
        update(JSON_T_ARRAY_END, None)
        return
    if isinstance(node, bool):
        update(JSON_T_TRUE if node else JSON_T_FALSE, node)
        return
    if node is None:
        update(JSON_T_NULL, None)
        return
    if isinstance(node, str):
        update(JSON_T_STRING, string_fun(node) if string_fun else node)
        return
    if isinstance(node, int) and ints:
        update(JSON_T_INTEGER, node)
        return
    update(JSON_T_FLOAT, float(node))


def isValidJSON(content, as_text=None) -> bool:
    """TRUE when libjson accepts the text or the file."""
    if isinstance(content, AsIs):
        content = content.value
        as_text = True
    if not isinstance(content, str):
        return False
    try:
        if not _as_text(content, as_text):
            content = _read_text(content)
        _loads(content)
    except (RJSONIOError, OSError, UnicodeError):
        return False
    return True


def pretty_json(text: str) -> str:
    """libjson's formatted rewrite. Infinity does not survive the reparse."""
    prepared = text.replace(" - Infinity", " null").replace(" Infinity", " null")
    try:
        value = json.loads(prepared)
    except json.JSONDecodeError as exc:
        raise RJSONIOError("couldn't parse the JSON content") from exc
    return _pretty(value, 0)


def _pretty(value, indent: int) -> str:
    pad = "\t" * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        items = list(value.items())
        for index, (key, item) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            lines.append(f"{pad}\t{json.dumps(key)} : {_pretty(item, indent + 1)}{comma}")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = ["["]
        for index, item in enumerate(value):
            comma = "," if index < len(value) - 1 else ""
            lines.append(f"{pad}\t{_pretty(item, indent + 1)}{comma}")
        lines.append(f"{pad}]")
        return "\n".join(lines)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float) and value.is_integer() and abs(value) < 2**53:
        return str(int(value))
    return json.dumps(value)


def _skip_json_space(text: str, index: int) -> int:
    size = len(text)
    while index < size:
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("//", index):
            index += 2
            while index < size and text[index] != "\n":
                index += 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                return index
            index = end + 2
            continue
        break
    return index


def _find_json_value_end(text: str, start: int) -> int | None:
    index = _skip_json_space(text, start)
    if index >= len(text):
        return None
    if text[index] not in "[{":
        raise RJSONIOError("invalid JSON input")
    stack = [text[index]]
    index += 1
    in_string = False
    escaped = False
    size = len(text)
    while index < size:
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if text.startswith("//", index):
            index += 2
            while index < size and text[index] != "\n":
                index += 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                return None
            index = end + 2
            continue
        if char in "[{":
            stack.append(char)
        elif char == "]":
            if not stack or stack[-1] != "[":
                raise RJSONIOError("invalid JSON input")
            stack.pop()
            if not stack:
                return index + 1
        elif char == "}":
            if not stack or stack[-1] != "{":
                raise RJSONIOError("invalid JSON input")
            stack.pop()
            if not stack:
                return index + 1
        index += 1
    return None


def _read_stream_chunk(handle, size: int = 1024) -> str:
    data = handle.read(size)
    if not data:
        return ""
    if isinstance(data, bytes):
        return data.decode("latin-1")
    return data


def _open_stream(con):
    if hasattr(con, "read"):
        return con, lambda: None
    if isinstance(con, str):
        if os.path.isfile(con):
            handle = open(con, "rb")
            return handle, handle.close
        raise RJSONIOError("invalid JSON input")
    raise RJSONIOError("readJSONStream() expects a file path or a readable stream.")


def _consume_stream_values(buffer: str) -> tuple[list, str]:
    values = []
    while True:
        start = _skip_json_space(buffer, 0)
        if start >= len(buffer):
            return values, ""
        end = _find_json_value_end(buffer, start)
        if end is None:
            return values, buffer[start:]
        piece = buffer[start:end]
        values.append(_loads(piece))
        buffer = buffer[end:]


def readJSONStream(con, cb=None, simplify: int = Strict, null_value=None, simplify_with_names: bool = True):
    """Read one or more JSON values from a file path or a byte stream."""
    handle, closer = _open_stream(con)
    buffer = ""
    last = None
    try:
        while True:
            chunk = _read_stream_chunk(handle, 1024)
            if not chunk:
                break
            buffer += chunk
            parsed, buffer = _consume_stream_values(buffer)
            for tree in parsed:
                value = _simplify_node(tree, int(simplify), null_value, bool(simplify_with_names))
                if cb is not None:
                    last = cb(value)
                else:
                    last = value
        if buffer.strip():
            parsed, remainder = _consume_stream_values(buffer)
            if remainder.strip():
                raise RJSONIOError("invalid JSON input")
            for tree in parsed:
                value = _simplify_node(tree, int(simplify), null_value, bool(simplify_with_names))
                if cb is not None:
                    last = cb(value)
                else:
                    last = value
    finally:
        closer()
    return last
