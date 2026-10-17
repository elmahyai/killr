"""yaml.load: a YAML 1.1 document into R-shaped Python values.

PyYAML walks the events. Tags, merges, and vector coercion follow CRAN yaml.
"""

import copy
import math
import warnings

import yaml
from yaml.events import (
    AliasEvent,
    DocumentEndEvent,
    DocumentStartEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
    StreamEndEvent,
)

from r_yaml.classify import tag_from_event


def _short_tag(tag):
    if not tag:
        return None
    if tag.startswith("tag:yaml.org,2002:"):
        return tag[len("tag:yaml.org,2002:") :]
    while tag.startswith("!"):
        tag = tag[1:]
    return tag or None
from r_yaml.types import (
    NA,
    NA_CHARACTER,
    NA_INTEGER,
    NA_LOGICAL,
    NA_REAL,
    BadAnchor,
    DataFrame,
    MergeKey,
    Record,
    Vector,
    kind_of,
)

_MISSING = object()
options = {"yaml.eval.expr": None}

_INT_MIN = -2147483648
_INT_MAX = 2147483647


class YamlError(ValueError):
    pass


def _warn(message):
    warnings.warn(message, stacklevel=3)


def _prefix(label, message):
    if label:
        return f"({label}) {message}"
    return message


def _handler(handlers, tag):
    if not handlers or tag not in handlers:
        return None
    if tag == "merge":
        _warn("Custom handling for type 'merge' is not allowed; handler ignored")
        return None
    return handlers[tag]


def _run_handler(function, value, tag):
    try:
        return function(value), True
    except Exception:
        _warn(f"an error occurred when handling type '{tag}'; using default handler")
        return None, False


def _convert_scalar(text, tag, handlers, eval_expr, eval_warning):
    function = _handler(handlers, tag)
    if function is not None:
        result, ok = _run_handler(function, text, tag)
        if ok:
            return result
    if tag == "str" or tag.startswith("timestamp"):
        return text
    if tag in ("int#base60", "float#base60"):
        return text
    if tag == "int#na":
        return NA_INTEGER
    if tag == "int" or tag.startswith("int#"):
        return _as_int(text, tag)
    if tag in ("float", "float#fix", "float#exp"):
        return _as_float(text)
    if tag == "bool":
        inner = tag_from_event(_Plain(text))
        if inner == "bool#yes":
            return True
        if inner == "bool#no":
            return False
        if inner == "bool#na":
            return NA_LOGICAL
        _warn(f"NAs introduced by coercion: {text} is not a recognized boolean value")
        return NA_LOGICAL
    if tag == "bool#yes":
        return True
    if tag == "bool#no":
        return False
    if tag == "bool#na":
        return NA_LOGICAL
    if tag == "float#na":
        return NA_REAL
    if tag == "float#nan":
        return float("nan")
    if tag == "float#inf":
        return float("inf")
    if tag == "float#neginf":
        return float("-inf")
    if tag == "str#na":
        return NA_CHARACTER
    if tag == "null":
        return None
    if tag == "merge":
        return MergeKey()
    if tag == "expr":
        if eval_expr:
            return _eval_expr(text)
        if eval_warning:
            _warn(
                "Evaluating R expressions (!expr) requires explicit `eval.expr=TRUE` option (see yaml.load help)"
            )
        return text
    if tag in ("seq", "map", "omap"):
        raise YamlError(f"Invalid tag for scalar: {tag}")
    return text


class _Plain:
    """A stand-in event so an explicit bool tag can be classified."""

    def __init__(self, value):
        self.value = value
        self.tag = None
        self.implicit = (True, False)


def _as_int(text, tag):
    base = 10
    token = text
    if tag == "int#hex":
        base = 16
    elif tag == "int#oct":
        base = 8
    try:
        number = int(token, base)
    except ValueError:
        _warn(f"NAs introduced by coercion: {text} is not an integer")
        return NA_INTEGER
    if number < _INT_MIN or number > _INT_MAX or number == _INT_MIN:
        _warn(f"NAs introduced by coercion: {text} is out of integer range")
        return NA_INTEGER
    return number


def _as_float(text):
    try:
        number = float(text)
    except ValueError:
        _warn(f"NAs introduced by coercion: {text} is not a real")
        return NA_REAL
    if math.isinf(number):
        _warn(f"NAs introduced by coercion: {text} is out of real range")
        return NA_REAL
    return number


def _eval_expr(text):
    try:
        result = eval(text, {"__builtins__": {}}, {})
    except Exception as exc:
        raise YamlError(f"Could not evaluate expression: {text}") from exc
    if type(result) is int:
        return float(result)
    return result


def _inspect(value):
    """format() of a value, for an illegal-merge message."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, NA):
        return "NA"
    if isinstance(value, float):
        return _format_real_token(value)
    if isinstance(value, (int, str)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_inspect(item) for item in value)
    return str(value)


def _format_real_token(number):
    return format(number, ".15g")


def _coerce_sequence(items):
    if not items:
        return Vector([], "character")
    kinds = []
    for item in items:
        if isinstance(item, (list, dict, Record, DataFrame)) and not isinstance(item, Vector):
            return list(items)
        if isinstance(item, Vector):
            return list(items)
        kind = kind_of(item)
        if kind is None:
            return list(items)
        kinds.append(kind)
    if len(set(kinds)) == 1:
        return Vector(items, kinds[0])
    return list(items)


def _key_string(key):
    if isinstance(key, bool):
        return "TRUE" if key else "FALSE"
    if isinstance(key, NA):
        return "NA"
    if key is None:
        return "NULL"
    return str(key)


def _same_key(left, right, named):
    if named:
        return _key_string(left) == _key_string(right)
    return left == right and type(left) is type(right)


class _MapBuilder:
    def __init__(self, named, merge_warning):
        self.named = named
        self.merge_warning = merge_warning
        self.entries = []

    def _find(self, key):
        for index, (existing, _value, _from_merge) in enumerate(self.entries):
            if _same_key(existing, key, self.named):
                return index
        return None

    def add(self, key, value, from_merge):
        stored = _key_string(key) if self.named else key
        found = self._find(stored if self.named else key)
        if found is None:
            self.entries.append((stored if self.named else key, value, from_merge))
            return
        _existing, _value, was_merge = self.entries[found]
        if not was_merge and not from_merge:
            raise YamlError(f"Duplicate map key: '{stored if self.named else key}'")
        if from_merge and self.merge_warning:
            _warn(f"Duplicate map key ignored during merge: '{stored if self.named else key}'")
        elif not from_merge and self.merge_warning:
            _warn(f"Duplicate map key ignored after merge: '{stored if self.named else key}'")

    def finish(self):
        if self.named:
            return {key: value for key, value, _from_merge in self.entries}
        return Record([(key, value) for key, value, _from_merge in self.entries])


def _expand_merge(value, builder):
    if isinstance(value, dict):
        pairs = list(value.items())
    elif isinstance(value, Record):
        pairs = value.pairs
    elif isinstance(value, list) and not isinstance(value, Vector):
        for item in value:
            if not isinstance(item, (dict, Record)):
                raise YamlError(f"Illegal merge: {_inspect(value)}")
            _expand_merge(item, builder)
        return
    else:
        raise YamlError(f"Illegal merge: {_inspect(value)}")
    for key, item in pairs:
        builder.add(key, item, True)


_SCALAR_TAGS = {
    "str",
    "seq",
    "int",
    "float",
    "bool",
    "omap",
    "merge",
    "expr",
    "null",
}


def _incompatible(tag):
    if tag is None or tag in ("map", "seq"):
        return False
    if tag in _SCALAR_TAGS or tag.startswith(("int#", "float#", "bool#", "str#")):
        return True
    return False


def _finish_map(pairs, tag, handlers, as_named_list, merge_override, merge_warning):
    if merge_override:
        builder = _MapBuilder(as_named_list, merge_warning)
        merges = []
        for key, value in pairs:
            if isinstance(key, MergeKey):
                merges.append(value)
            else:
                builder.add(key, value, False)
        for value in merges:
            _expand_merge(value, builder)
    else:
        builder = _MapBuilder(as_named_list, merge_warning)
        for key, value in pairs:
            if isinstance(key, MergeKey):
                _expand_merge(value, builder)
            else:
                builder.add(key, value, False)
    result = builder.finish()
    function = _handler(handlers, tag or "map")
    if function is not None:
        replaced, ok = _run_handler(function, result, tag or "map")
        if ok:
            return replaced
    if tag in (None, "map") or not _incompatible(tag):
        return result
    if tag == "null":
        return None
    raise YamlError(f"Invalid tag: {tag} for map")


def _finish_seq(items, tag, handlers, as_named_list):
    if tag == "omap":
        return _finish_omap(items, as_named_list)
    function = _handler(handlers, tag or "seq")
    if function is not None:
        replaced, ok = _run_handler(function, list(items), tag or "seq")
        if ok:
            return replaced
    if tag in (None, "seq") or not _incompatible(tag):
        return _coerce_sequence(items)
    if tag == "null":
        return None
    raise YamlError(f"Invalid tag: {tag} for sequence")


def _finish_omap(items, as_named_list):
    pairs = []
    for item in items:
        if isinstance(item, dict):
            entries = list(item.items())
        elif isinstance(item, Record):
            entries = item.pairs
        else:
            raise YamlError("omap must be a sequence of maps")
        pairs.extend(entries)
    seen = []
    for key, _value in pairs:
        if any(_same_key(key, previous, as_named_list) for previous in seen):
            raise YamlError(f"Duplicate omap key: '{key}'")
        seen.append(key)
    if as_named_list:
        return {(_key_string(key) if not isinstance(key, str) else key): value for key, value in pairs}
    return Record(pairs)


def _copy(value):
    return copy.deepcopy(value)


def yaml_load(
    string,
    as_named_list=True,
    handlers=None,
    error_label=None,
    eval_expr=_MISSING,
    merge_precedence="order",
    merge_warning=False,
):
    """Parse one YAML string. Uniform sequences become vectors. Maps become dicts."""
    if isinstance(string, (list, tuple)):
        string = "\n".join("" if part is None else str(part) for part in string)
    elif string is None:
        string = ""
    else:
        string = str(string)
    if merge_precedence not in ("order", "override"):
        raise ValueError("merge_precedence must be 'order' or 'override'")
    if handlers and "merge" in handlers:
        _warn("Custom handling for type 'merge' is not allowed; handler ignored")
        handlers = {key: value for key, value in handlers.items() if key != "merge"}
    if eval_expr is _MISSING:
        option = options.get("yaml.eval.expr")
        eval_warning = option is None
        eval_expr = False if option is None else bool(option)
    else:
        eval_warning = False
    try:
        events = list(yaml.parse(string))
    except yaml.YAMLError as exc:
        raise YamlError(_prefix(error_label, str(exc))) from exc
    try:
        return _walk(
            events,
            as_named_list,
            handlers,
            eval_expr,
            eval_warning,
            merge_precedence == "override",
            merge_warning,
        )
    except YamlError as exc:
        raise YamlError(_prefix(error_label, str(exc))) from exc


def _walk(events, as_named_list, handlers, eval_expr, eval_warning, merge_override, merge_warning):
    stack = []
    anchors = {}
    result = None
    saw_document = False
    for event in events:
        if isinstance(event, (DocumentStartEvent, StreamEndEvent)):
            continue
        if isinstance(event, DocumentEndEvent):
            break
        if isinstance(event, ScalarEvent):
            tag = tag_from_event(event)
            value = _convert_scalar(event.value, tag, handlers, eval_expr, eval_warning)
            if event.anchor:
                anchors[event.anchor] = _copy(value)
            _push(stack, value)
            saw_document = True
        elif isinstance(event, SequenceStartEvent):
            stack.append(("seq", event.anchor, _short_tag(event.tag), []))
            saw_document = True
        elif isinstance(event, SequenceEndEvent):
            kind, anchor, tag, items = stack.pop()
            value = _finish_seq(items, tag, handlers, as_named_list)
            if anchor:
                anchors[anchor] = _copy(value)
            _push(stack, value)
        elif isinstance(event, MappingStartEvent):
            stack.append(("map", event.anchor, _short_tag(event.tag), []))
            saw_document = True
        elif isinstance(event, MappingEndEvent):
            kind, anchor, tag, pairs = stack.pop()
            value = _finish_map(pairs, tag, handlers, as_named_list, merge_override, merge_warning)
            if anchor:
                anchors[anchor] = _copy(value)
            _push(stack, value)
        elif isinstance(event, AliasEvent):
            if event.anchor not in anchors:
                _warn(f"Unknown anchor: {event.anchor}")
                value = BadAnchor()
            else:
                value = _copy(anchors[event.anchor])
            _push(stack, value)
            saw_document = True
    if not saw_document:
        return None
    if len(stack) != 1:
        raise YamlError("Could not parse expression")
    result = stack[0]
    return result


def _push(stack, value):
    if not stack:
        stack.append(value)
        return
    top = stack[-1]
    if isinstance(top, tuple) and top[0] == "seq":
        top[3].append(value)
        return
    if isinstance(top, tuple) and top[0] == "map":
        pairs = top[3]
        if not pairs or isinstance(pairs[-1], tuple):
            pairs.append(value)
        else:
            key = pairs.pop()
            pairs.append((key, value))
        return
    stack.append(value)
