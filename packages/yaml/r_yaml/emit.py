"""as.yaml: R values to a YAML 1.1 string.

PyYAML's dump quotes and indents differently, and it writes true/false.
Logicals here are yes/no, and the indent follows CRAN yaml.
"""

import math

from r_yaml.classify import implicit_tag
from r_yaml.types import NA, NA_CHARACTER, NA_INTEGER, NA_LOGICAL, NA_REAL, DataFrame, Record, Vector, Verbatim


def _format_real(number, precision):
    if isinstance(number, NA):
        return ".na.real"
    if math.isnan(number):
        return ".nan"
    if math.isinf(number):
        return "-.inf" if number < 0 else ".inf"
    scientific = False
    if number != 0 and not (number == 0 and math.copysign(1.0, number) < 0):
        exponent = math.log10(abs(number))
        scientific = exponent < -4 or exponent >= precision
    if number == 0:
        scientific = False
    if scientific:
        text = format(number, f".{precision}e")
        mantissa, exponent = text.split("e")
        return _trim_mantissa(mantissa) + "e" + exponent
    text = format(number, f".{precision}f")
    return _trim_mantissa(text)


def _trim_mantissa(text):
    if "." not in text:
        return text
    index = len(text) - 1
    while index > 0 and text[index] == "0" and text[index - 1] != ".":
        index -= 1
    return text[: index + 1]


def _format_scalar(value, precision):
    if value is None:
        return "~"
    if isinstance(value, NA):
        return {
            "logical": ".na",
            "integer": ".na.integer",
            "real": ".na.real",
            "character": ".na.character",
        }[value.kind]
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_real(value, precision)
    return str(value)


def _quote_plain(text, quoted, verbatim, unicode):
    if verbatim:
        return text
    if quoted or (unicode is False and any(ord(char) > 127 for char in text)):
        return _double_quote(text, unicode)
    if "\n" in text:
        return None
    tag = implicit_tag(text)
    if tag not in ("str", "str#na"):
        return "'" + text.replace("'", "''") + "'"
    if text == "" or _needs_quotes(text):
        return "'" + text.replace("'", "''") + "'"
    return text


def _needs_quotes(text):
    if text[0] in "!&*'\"%@`|>,[]{}?":
        return True
    if ": " in text or text.endswith(":"):
        return True
    if " #" in text or text.startswith("#"):
        return True
    if text[0] in " \t" or text[-1] in " \t":
        return True
    return False


def _double_quote(text, unicode):
    pieces = ['"']
    for char in text:
        code = ord(char)
        if char == "\\":
            pieces.append("\\\\")
        elif char == '"':
            pieces.append('\\"')
        elif char == "\n":
            pieces.append("\\n")
        elif unicode is False and code > 127:
            if code <= 255:
                pieces.append(f"\\x{code:02X}")
            else:
                pieces.append(f"\\u{code:04X}")
        else:
            pieces.append(char)
    pieces.append('"')
    return "".join(pieces)


def _block(text, content_column, indent_width):
    """A literal block. A string that is only a newline uses |indent+."""
    if text == "\n":
        return f"|{indent_width}+\n"
    if text.endswith("\n\n"):
        chomp = "+"
        body = text[:-1]
    elif text.endswith("\n"):
        chomp = ""
        body = text[:-1]
    else:
        chomp = "-"
        body = text
    lines = body.split("\n")
    indicator = str(indent_width) if lines and lines[0] == "" else ""
    pad = " " * content_column
    content = "\n".join(pad + line if line else "" for line in lines)
    return f"|{indicator}{chomp}\n{content}"


class _Emitter:
    def __init__(self, indent, omap, column_major, unicode, precision, indent_mapping_sequence, handlers):
        if not isinstance(indent, int) or isinstance(indent, bool) or indent <= 0:
            raise ValueError("argument `indent` must be greater than 0")
        if not isinstance(precision, int) or isinstance(precision, bool) or not 1 <= precision <= 22:
            raise ValueError("precision must be in the range 1..22")
        self.indent = indent
        self.omap = omap
        self.column_major = column_major
        self.unicode = unicode
        self.precision = precision
        self.indent_mapping_sequence = indent_mapping_sequence
        self.handlers = handlers or {}

    def emit(self, value):
        lines = self._lines(value, 0, omap=self.omap)
        text = "\n".join(lines)
        if not text.endswith("\n"):
            text += "\n"
        return text

    def _apply(self, value):
        classes = list(getattr(value, "classes", ()))
        if isinstance(value, bool):
            classes.append("logical")
        elif isinstance(value, NA) and value.kind == "logical":
            classes.append("logical")
        elif isinstance(value, int) and not isinstance(value, bool):
            classes.append("integer")
        elif isinstance(value, float) or (isinstance(value, NA) and value.kind == "real"):
            classes.append("numeric")
        elif isinstance(value, str):
            classes.append("character")
        elif isinstance(value, DataFrame):
            classes.append("data.frame")
        elif isinstance(value, Vector):
            classes.append(
                {"integer": "integer", "real": "numeric", "logical": "logical", "character": "character"}[
                    value.kind
                ]
            )
        elif isinstance(value, dict):
            classes.append("list")
        for name in classes:
            if name in self.handlers:
                return self._apply(self.handlers[name](value))
        return value

    def _lines(self, value, column, omap=False):
        value = self._apply(value)
        if omap and isinstance(value, dict):
            tag = getattr(value, "tag", None) or "!!omap"
            return self._omap(list(value.items()), column, tag)
        if isinstance(value, Verbatim):
            return self._sequence_values(list(value), column, None, verbatim=True)
        if isinstance(value, DataFrame):
            return self._frame(value, column)
        if isinstance(value, Vector):
            return self._vector(value, column)
        if isinstance(value, Record):
            return self._sequence_values([item for _key, item in value.pairs], column, None)
        if isinstance(value, dict):
            return self._mapping(list(value.items()), column, getattr(value, "tag", None))
        if isinstance(value, list):
            return self._sequence_values(value, column, getattr(value, "tag", None))
        if callable(value) and not isinstance(value, type):
            return self._function(value, column)
        return self._scalar_lines(value, column)

    def _scalar_lines(self, value, column, quoted=False):
        tag = getattr(value, "tag", None)
        quoted = quoted or bool(getattr(value, "quoted", False))
        verbatim = "verbatim" in getattr(value, "classes", ())
        if value is None:
            text = "~"
        elif isinstance(value, str):
            rendered = _quote_plain(value, quoted, verbatim, self.unicode)
            if rendered is None:
                text = _block(value, column + self.indent, self.indent)
            else:
                text = rendered
        else:
            text = _format_scalar(value, self.precision)
        if tag and "\n" not in text:
            text = f"{tag} {text}"
        elif tag:
            text = f"{tag} {text}"
        if "\n" in text:
            return text.split("\n")
        return [text]

    def _attach(self, prefix, value, container):
        """Place value after 'key: ' or '- '. container is the key or dash column."""
        key_prefix = prefix.rstrip().endswith(":")
        if isinstance(value, DataFrame) and not value.columns:
            return [prefix + "{}"]
        if isinstance(value, dict) and not value:
            return [prefix + "{}"]
        if isinstance(value, list) and not value:
            return [prefix + "[]"]
        if key_prefix and self._is_sequence(value):
            dash_column = container + self.indent if self.indent_mapping_sequence else container
            return [prefix.rstrip(), *self._lines(value, dash_column, omap=self.omap)]
        if isinstance(value, str) and "\n" in value:
            rendered = self._scalar_lines(value, container)
            return [prefix + rendered[0], *rendered[1:]]
        if self._is_collection(value):
            if self.omap and isinstance(value, dict):
                child = container
            else:
                child = container + (2 if prefix.endswith("- ") else self.indent)
            rendered = self._lines(value, child, omap=self.omap)
            if (
                key_prefix
                and rendered
                and not rendered[0].startswith(" ")
                and not self._is_sequence(value)
            ):
                return [prefix + rendered[0], *rendered[1:]]
            pad = " " * child
            first, *rest = rendered
            if first.startswith(pad):
                first = first[len(pad) :]
            if prefix.endswith("- "):
                return [prefix + first, *rest]
            return [prefix.rstrip(), *rendered]
        rendered = self._lines(value, container, omap=self.omap)
        if rendered and rendered[0].startswith("|"):
            return [prefix + rendered[0], *rendered[1:]]
        return [prefix + rendered[0]]

    def _vector(self, value, column):
        if len(value) <= 1 and not value.tag:
            item = value[0] if value else ""
            return self._scalar_lines(item if value else "", column, quoted=value.quoted) if value else ["[]"]
        if len(value) == 1 and value.tag:
            body = self._scalar_lines(value[0], column, quoted=value.quoted)
            if body[0].startswith("|"):
                return [f"{value.tag} {body[0]}", *body[1:]]
            return [f"{value.tag} {body[0]}"]
        lines = []
        if value.tag:
            lines.append(value.tag)
        lines.extend(self._sequence_values(list(value), column, None))
        return lines

    def _sequence_values(self, values, column, tag, verbatim=False):
        lines = []
        if tag:
            lines.append(tag)
        if not values:
            lines.append("[]")
            return lines
        pad = " " * column
        for item in values:
            if verbatim and isinstance(item, str):
                rendered = [_quote_plain(item, False, True, self.unicode) or item]
                lines.append(f"{pad}- {rendered[0]}")
                continue
            child = self._attach(f"{pad}- ", item, column)
            lines.extend(child)
        return lines

    def _mapping(self, pairs, column, tag):
        lines = []
        if tag:
            lines.append(tag)
        if not pairs:
            lines.append("{}")
            return lines
        pad = " " * column
        for key, value in pairs:
            key_text = self._key(key)
            lines.extend(self._attach(f"{pad}{key_text}: ", value, column))
        return lines

    def _is_collection(self, value):
        return isinstance(value, (dict, list, DataFrame, Vector, Verbatim)) and not (
            isinstance(value, Vector) and len(value) <= 1
        )

    def _is_sequence(self, value):
        value = value
        if isinstance(value, DataFrame):
            return not self.column_major
        if isinstance(value, Vector):
            return len(value) > 1
        if isinstance(value, Verbatim):
            return len(value) > 1
        return isinstance(value, list)

    def _omap(self, pairs, column, tag):
        lines = [tag]
        pad = " " * column
        for key, value in pairs:
            lines.extend(self._attach(f"{pad}- {self._key(key)}: ", value, column + 2))
        return lines

    def _frame(self, frame, column):
        columns = frame.columns
        if not columns:
            lines = ["{}"]
            if frame.tag:
                lines.insert(0, frame.tag)
            return lines
        if self.column_major:
            pairs = []
            for name, column_values in columns.items():
                if not isinstance(column_values, Vector):
                    sample = column_values[0] if len(column_values) else ""
                    if isinstance(sample, bool):
                        kind = "logical"
                    elif isinstance(sample, int):
                        kind = "integer"
                    elif isinstance(sample, float):
                        kind = "real"
                    else:
                        kind = "character"
                    column_values = Vector(list(column_values), kind, tag=getattr(column_values, "tag", None))
                pairs.append((name, column_values))
            return self._mapping(pairs, column, frame.tag)
        names = list(columns)
        rows = zip(*[list(column_values) for column_values in columns.values()])
        items = [dict(zip(names, row)) for row in rows]
        return self._sequence_values(items, column, frame.tag)

    def _function(self, value, column):
        try:
            import inspect

            source = inspect.getsource(value).strip("\n")
        except (OSError, TypeError):
            source = repr(value)
        pad = " " * (column + self.indent)
        lines = ["!expr |"]
        lines.extend(pad + line for line in source.split("\n"))
        return lines

    def _key(self, key):
        text = key if isinstance(key, str) else _format_scalar(key, self.precision)
        rendered = _quote_plain(str(text), False, False, self.unicode)
        if rendered is None:
            rendered = "'" + str(text).replace("'", "''") + "'"
        return rendered


def as_yaml(
    x,
    line_sep="\n",
    indent=2,
    omap=False,
    column_major=True,
    unicode=True,
    precision=7,
    indent_mapping_sequence=False,
    handlers=None,
):
    """Convert a value to a YAML string. Logicals are yes and no."""
    if line_sep not in ("\n", "\r\n", "\r"):
        raise ValueError("line_sep must be '\\n', '\\r\\n', or '\\r'")
    emitter = _Emitter(
        indent,
        omap,
        column_major,
        unicode,
        precision,
        indent_mapping_sequence,
        handlers,
    )
    text = emitter.emit(x)
    if line_sep != "\n":
        text = text.replace("\n", line_sep)
    return text
