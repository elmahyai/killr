"""HTML dependencies from htmltools 0.5.9.

``htmlDependency`` stores a named list of class ``html_dependency``.
``version`` is passed through ``as.character`` before it is checked.
``name`` is checked and stored as it was supplied. A ``src`` element whose
name is missing or ``""`` is named ``file``. ``nzchar(NA)`` is true, so a
missing name is left missing. ``NULL`` ``src`` fails when the names are
assigned, with "attempt to set an attribute on NULL".

R warns when the caller is a namespace and any ``src`` element begins with
``/``. Python has no R namespace, so that warning is raised only when
``_namespace`` is true.
"""

from __future__ import annotations

import math
import warnings

from htmltools.escape import NA, _character_double, is_na

_MISSING = object()

_INVALID_TAIL = " (must be a non-empty character string and contain no '/' or '\\')"
_NAMESPACE_WARNING = (
    "htmlDependency shouldn't be called from a namespace environment"
    " with absolute paths (or paths from system.file())."
    " See ?htmlDependency for more information."
)


class Atom:
    """An R atomic vector. A missing element is ``NA``."""

    def __init__(self, mode: str, data: list, names: list | None):
        self.mode = mode
        self.data = data
        self.names = names


class Listing:
    """An R list. ``names`` is ``None`` when the names attribute is NULL."""

    def __init__(self, items: list, names: list | None):
        self.items = items
        self.names = names


class HtmlDependency:
    """A list of class ``html_dependency``."""

    def __init__(self, name, version, src, meta, script, stylesheet, head, attachment, package, all_files):
        self.name = name
        self.version = version
        self.src = src
        self.meta = meta
        self.script = script
        self.stylesheet = stylesheet
        self.head = head
        self.attachment = attachment
        self.package = package
        self.all_files = all_files
        self.r_class = "html_dependency"


def _invalid(label: str) -> str:
    return "Invalid argument '" + label + "'" + _INVALID_TAIL


def _is_pairs(values) -> bool:
    if len(values) == 0:
        return False
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            return False
        key = item[0]
        if not isinstance(key, str) and not is_na(key):
            return False
    return True


def _nested(value) -> bool:
    return value is None or isinstance(value, (dict, list, tuple))


def _mode(values) -> str:
    saw_character = False
    saw_complex = False
    saw_double = False
    saw_integer = False
    for value in values:
        if is_na(value) or value is None:
            continue
        if isinstance(value, str):
            saw_character = True
        elif isinstance(value, complex):
            saw_complex = True
        elif isinstance(value, float):
            saw_double = True
        elif isinstance(value, bool):
            continue
        elif isinstance(value, int):
            saw_integer = True
    if saw_character:
        return "character"
    if saw_complex:
        return "complex"
    if saw_double:
        return "double"
    if saw_integer:
        return "integer"
    return "logical"


def _character_complex(value: complex) -> str:
    """R ``as.character`` of one complex number."""

    real = _character_double(float(value.real))
    imag = float(value.imag)
    if imag < 0.0 or (imag == 0.0 and math.copysign(1.0, imag) < 0.0):
        return real + "-" + _character_double(abs(imag)) + "i"
    return real + "+" + _character_double(imag) + "i"


def _from_mode(mode: str, element):
    if element is NA:
        return NA
    if mode == "character":
        return element
    if mode == "logical":
        return "TRUE" if element else "FALSE"
    if mode == "integer":
        return str(element)
    if mode == "double":
        return _character_double(element)
    return _character_complex(element)


def _coerce(value, mode: str):
    if is_na(value):
        return NA
    if mode == "character":
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return _character_double(value)
        if isinstance(value, complex):
            return _character_complex(value)
        return str(value)
    if mode == "logical":
        return value
    if mode == "integer":
        if isinstance(value, bool):
            return 1 if value else 0
        return value
    if mode == "double":
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, int):
            return float(value)
        return value
    if isinstance(value, complex):
        return value
    if isinstance(value, bool):
        return complex(1.0 if value else 0.0, 0.0)
    return complex(float(value), 0.0)


def _atomic_sequence(values) -> Atom:
    if len(values) == 0:
        return Atom("character", [], None)
    if any(_nested(value) for value in values):
        raise RuntimeError("sequence is a list")
    mode = _mode(values)
    return Atom(mode, [_coerce(value, mode) for value in values], None)


def interpret(value):
    """Turn a Python value into the R object ``htmlDependency`` stores.

    ``None`` is ``NULL``. ``NA`` is logical ``NA``. A string, number, or
    logical is a length-one atomic vector. A flat sequence of those is an
    atomic vector, and ``c()`` would coerce it the same way. A dict, or a
    sequence of ``(name, value)`` pairs, is an R list, so a missing element
    stays ``NULL`` and a blank name stays blank.
    """

    if value is None:
        return None
    if is_na(value):
        return Atom("logical", [NA], None)
    if isinstance(value, (Atom, Listing, HtmlDependency)):
        return value
    if isinstance(value, str):
        return Atom("character", [value], None)
    if isinstance(value, bool):
        return Atom("logical", [value], None)
    if isinstance(value, int):
        return Atom("integer", [value], None)
    if isinstance(value, float):
        return Atom("double", [value], None)
    if isinstance(value, complex):
        return Atom("complex", [value], None)
    if isinstance(value, dict):
        items = [interpret(item) for item in value.values()]
        names = list(value.keys())
        # ``list()`` has a NULL names attribute. An empty dict is that list.
        if len(names) == 0:
            names = None
        return Listing(items, names)
    if isinstance(value, (list, tuple)):
        if _is_pairs(value):
            names = []
            items = []
            for key, item in value:
                names.append(NA if is_na(key) else key)
                items.append(interpret(item))
            return Listing(items, names)
        if any(_nested(item) for item in value):
            return Listing([interpret(item) for item in value], None)
        return _atomic_sequence(value)
    raise ValueError(
        f"cannot coerce type '{type(value).__name__}' to vector of type 'character'"
    )


def _length(obj) -> int:
    if obj is None:
        return 0
    if isinstance(obj, Atom):
        return len(obj.data)
    if isinstance(obj, Listing):
        return len(obj.items)
    return 1


def as_character(obj) -> Atom:
    """R ``as.character``. A top-level ``NULL`` is ``character(0)``."""

    if obj is None:
        return Atom("character", [], None)
    if isinstance(obj, Atom):
        return Atom("character", [_from_mode(obj.mode, element) for element in obj.data], None)
    data = []
    for item in obj.items:
        if item is None:
            data.append("NULL")
        else:
            data.extend(as_character(item).data)
    return Atom("character", data, None)


def _eq_empty(obj):
    """The single comparison ``x == ""``. ``NA`` means the result is missing."""

    if isinstance(obj, Atom):
        element = obj.data[0]
        if element is NA:
            return NA
        if obj.mode == "character":
            return element == ""
        return False
    text = as_character(obj)
    if len(text.data) != 1:
        return False
    element = text.data[0]
    if element is NA:
        return NA
    return element == ""


def _has_slash(obj) -> bool:
    """``grepl("[/\\\\]", x)``. A missing string is not a match."""

    text = as_character(obj)
    if len(text.data) != 1:
        return False
    element = text.data[0]
    if element is NA:
        return False
    return "/" in element or "\\" in element


def _validate(obj, label: str) -> None:
    # ``||`` stops on the first true comparison. A missing ``== ""`` still
    # evaluates ``grepl``, and ``NA || FALSE`` is the missing-value error.
    if _length(obj) != 1:
        raise ValueError(_invalid(label))
    empty = _eq_empty(obj)
    if empty is True:
        raise ValueError(_invalid(label))
    slash = _has_slash(obj)
    if empty is NA:
        if slash:
            raise ValueError(_invalid(label))
        raise ValueError("missing value where TRUE/FALSE needed")
    if slash:
        raise ValueError(_invalid(label))


def _any_absolute(src):
    """``any(substr(src, 1, 1) == "/")``.

    ``NULL`` contributes no elements, so the result is false. A missing
    string makes the result missing unless some other element matches.
    """

    if src is None:
        return False
    text = as_character(interpret(src))
    saw_missing = False
    for element in text.data:
        if element is NA:
            saw_missing = True
        elif element[:1] == "/":
            return True
    if saw_missing:
        return NA
    return False


def _normalize_src(src) -> Listing:
    if src is None:
        raise ValueError("attempt to set an attribute on NULL")
    obj = interpret(src)
    if isinstance(obj, Atom):
        items = [Atom(obj.mode, [element], None) for element in obj.data]
        names = obj.names
    else:
        items = list(obj.items)
        names = obj.names
    if names is None:
        names = [""] * len(items)
    else:
        names = list(names)
    fixed = []
    for name in names:
        # ``nzchar(NA)`` is true, so only a blank name becomes ``file``.
        if name == "":
            fixed.append("file")
        else:
            fixed.append(name)
    return Listing(items, fixed)


def _store(value):
    if value is None:
        return None
    return interpret(value)


def htmlDependency(
    name=_MISSING,
    version=_MISSING,
    src=_MISSING,
    meta=None,
    script=None,
    stylesheet=None,
    head=None,
    attachment=None,
    package=None,
    all_files=True,
    *,
    _namespace=False,
):
    """Define one HTML dependency.

    ``name`` and ``version`` must each be one non-empty value and must not
    contain ``/`` or ``\\``. ``version`` is coerced with ``as.character``
    first. ``src`` is a path, a vector of paths, a dict of named paths, or
    a list of ``(name, value)`` pairs. Blank source names are stored as
    ``file``. The other arguments are stored unchanged. ``all_files``
    defaults to true.

    ``_namespace`` stands in for R's ``isNamespace(parent.frame())``. When
    it is true and a source path begins with ``/``, the namespace warning
    is signaled and the dependency is still returned.
    """

    if _namespace:
        if src is _MISSING:
            raise ValueError('argument "src" is missing, with no default')
        absolute = _any_absolute(src)
        if absolute is NA:
            raise ValueError("missing value where TRUE/FALSE needed")
        if absolute:
            warnings.warn(_NAMESPACE_WARNING, UserWarning, stacklevel=2)
    if version is _MISSING:
        raise ValueError('argument "version" is missing, with no default')
    if name is _MISSING:
        raise ValueError('argument "name" is missing, with no default')
    version_text = as_character(interpret(version))
    _validate(interpret(name), "name")
    _validate(version_text, "version")
    if src is _MISSING:
        raise ValueError('argument "src" is missing, with no default')
    return HtmlDependency(
        interpret(name),
        version_text,
        _normalize_src(src),
        _store(meta),
        _store(script),
        _store(stylesheet),
        _store(head),
        _store(attachment),
        _store(package),
        _store(all_files),
    )
