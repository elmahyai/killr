"""intersect from generics 0.1.4.

``intersect`` is ``UseMethod("intersect")``. Dispatch walks the class vector
for ``x`` the same way as the other generics in this package. The package
also registers ``intersect.default``, which forwards to ``base::intersect``;
proofs register their own methods and drop that default.

Argument matching follows formals ``x``, ``y``, and ``...``. Prefix rules
apply separately to ``x`` and ``y``. When ``x`` is not supplied, dispatch
uses the first ``...`` value, then ``y`` if it was supplied.
"""

from __future__ import annotations

import inspect
import threading


MISSING = object()
_METHODS: dict[str, object] = {}
_S4: dict[str, tuple[str, ...]] = {}
_LOCAL = threading.local()

_TAIL = {
    "double": ("double", "numeric"),
    "integer": ("integer", "numeric"),
    "logical": ("logical",),
    "character": ("character",),
    "complex": ("complex",),
    "raw": ("raw",),
    "list": ("list",),
}


class IntersectError(Exception):
    """An R ``stop`` from ``UseMethod`` or from the matched method."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Object:
    """An R object with an explicit class vector."""

    def __init__(self, value, classes, s4=False):
        self.value = value
        self.classes = tuple(classes)
        self.s4 = s4


class List:
    """An R list. A Python list of numbers is an atomic vector instead."""

    def __init__(self, values):
        self.values = list(values)


class Matrix:
    """A matrix. Values are stored in any order; dispatch only needs the kind."""

    def __init__(self, values, nrow, kind=None):
        self.values = list(values)
        self.nrow = int(nrow)
        self.ncol = len(self.values) // int(nrow) if nrow else 0
        self.kind = kind or _infer_kind(self.values)


class Array:
    """An array. A dim of length 2 is dispatched as a matrix, as in R."""

    def __init__(self, values, dim, kind=None):
        self.values = list(values)
        self.dim = tuple(dim)
        self.kind = kind or _infer_kind(self.values)


class _Frame:
    def __init__(self, classes, index, on_default, x, y, pos, kw):
        self.classes = classes
        self.index = index
        self.on_default = on_default
        self.x = x
        self.y = y
        self.obj = x
        self.pos = pos
        self.kw = kw


def missing(value):
    """R ``missing``. True when the argument was not supplied or was empty."""
    return value is MISSING


def force(value, *, name="x"):
    """R ``force``. Evaluating a missing argument is an error."""
    if value is MISSING:
        raise IntersectError(f'argument "{name}" is missing, with no default')
    return value


def register(class_name, fn):
    """Register ``intersect.<class_name>``. ``default`` is the fallback only."""
    _METHODS[class_name] = fn
    return fn


def unregister(*class_names):
    """Drop methods. Missing names are ignored."""
    for name in class_names:
        _METHODS.pop(name, None)


def reset_methods():
    """Drop every registered method. S4 contains stay."""
    _METHODS.clear()


def register_s4(class_name, contains):
    """Record S4 ``contains`` for ``class_name``, in ``is`` order."""
    _S4[class_name] = tuple(contains)


def next_method(generic=None):
    """R ``NextMethod``. The original arguments are matched again."""
    del generic
    frame = getattr(_LOCAL, "frame", None)
    if frame is None or frame.on_default:
        raise IntersectError("no method to invoke")
    for index in range(frame.index + 1, len(frame.classes)):
        name = frame.classes[index]
        if name is None:
            raise IntersectError("missing value where TRUE/FALSE needed")
        if name == "default":
            continue
        fn = _METHODS.get(name)
        if fn is not None:
            nxt = _Frame(
                frame.classes, index, False, frame.x, frame.y, frame.pos, frame.kw
            )
            return _run(fn, nxt)
    fn = _METHODS.get("default")
    if fn is not None:
        nxt = _Frame(
            frame.classes, len(frame.classes), True, frame.x, frame.y, frame.pos, frame.kw
        )
        return _run(fn, nxt)
    raise IntersectError(_no_method(frame.classes))


def intersect(*args, **kwargs):
    """Dispatch ``intersect`` on the class of ``x``."""
    x, y, pos, kw, explicit_x, omitted = _bind(args, kwargs)
    if explicit_x:
        passed_x = MISSING
        classes = ("name",)
    elif x is not MISSING:
        passed_x = x
        classes = _classes_of(x)
    elif omitted:
        if pos:
            dispatch = pos[0]
        elif kw:
            dispatch = next(iter(kw.values()))
        else:
            dispatch = None
        passed_x = MISSING
        classes = _classes_of(dispatch)
    else:
        if pos:
            dispatch = pos[0]
        elif kw:
            dispatch = next(iter(kw.values()))
        elif y is not MISSING:
            dispatch = y
        else:
            dispatch = None
        passed_x = MISSING
        classes = _classes_of(dispatch)
    found = _resolve(classes)
    if found is None:
        raise IntersectError(_no_method(classes))
    index, fn, on_default = found
    frame = _Frame(
        classes,
        0 if index is None else index,
        on_default,
        passed_x,
        y,
        pos,
        dict(kw),
    )
    return _run(fn, frame)


def _formal_key(formal, kwargs):
    exact = [key for key in kwargs if key == formal]
    partial = [
        key
        for key in kwargs
        if key and key != formal and formal.startswith(key)
    ]
    if len(exact) > 1 or (not exact and len(partial) > 1):
        raise IntersectError(
            f'formal argument "{formal}" matched by multiple actual arguments'
        )
    return exact[0] if exact else (partial[0] if partial else None)


def _bind(args, kwargs):
    x_key = _formal_key("x", kwargs)
    y_key = _formal_key("y", kwargs)
    used = {key for key in (x_key, y_key) if key is not None}
    dots = {key: value for key, value in kwargs.items() if key not in used}
    pos = list(args)
    explicit_x = False
    if x_key is not None:
        x = kwargs[x_key]
        explicit_x = x is MISSING
    elif pos:
        x = pos.pop(0)
    else:
        x = MISSING
    if y_key is not None:
        y = kwargs[y_key]
    elif pos:
        y = pos.pop(0)
    else:
        y = MISSING
    omitted = x_key is None and not args and y_key is None
    return x, y, tuple(pos), dots, explicit_x, omitted


def _classes_of(value):
    if value is None or value is MISSING:
        return ("NULL",)
    if isinstance(value, Object):
        if not value.classes:
            return _classes_of(value.value)
        if value.s4:
            return tuple(_expand_s4(value.classes))
        return tuple(value.classes)
    if isinstance(value, Matrix):
        return ("matrix", "array", *_TAIL[value.kind])
    if isinstance(value, Array):
        tail = _TAIL[value.kind]
        if len(value.dim) == 2:
            return ("matrix", "array", *tail)
        return ("array", *tail)
    if isinstance(value, List):
        return ("list",)
    if isinstance(value, bool):
        return ("logical",)
    if isinstance(value, int):
        return ("integer", "numeric")
    if isinstance(value, float):
        return ("double", "numeric")
    if isinstance(value, str):
        return ("character",)
    if isinstance(value, complex):
        return ("complex",)
    if isinstance(value, (list, tuple)):
        return _seq_classes(value)
    if callable(value):
        return ("function",)
    return ("list",)


def _expand_s4(classes):
    out = []
    seen = set()
    pending = list(classes)
    index = 0
    while index < len(pending):
        name = pending[index]
        index += 1
        if name in seen or name is None:
            if name is None:
                out.append(None)
            continue
        seen.add(name)
        out.append(name)
        for sup in _S4.get(name, ()):
            pending.append(sup)
    return out


def _seq_classes(values):
    if not values:
        return ("list",)
    if all(isinstance(item, bool) for item in values):
        return ("logical",)
    if all(isinstance(item, int) and not isinstance(item, bool) for item in values):
        return ("integer", "numeric")
    if all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in values
    ):
        return ("double", "numeric")
    if all(isinstance(item, str) for item in values):
        return ("character",)
    if all(isinstance(item, complex) for item in values):
        return ("complex",)
    return ("list",)


def _infer_kind(values):
    if values and all(isinstance(item, bool) for item in values):
        return "logical"
    if values and all(isinstance(item, int) and not isinstance(item, bool) for item in values):
        return "integer"
    if values and all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in values
    ):
        return "double"
    if values and all(isinstance(item, str) for item in values):
        return "character"
    if values and all(isinstance(item, complex) for item in values):
        return "complex"
    return "list"


def _resolve(classes):
    for index, name in enumerate(classes):
        if name is None:
            raise IntersectError("missing value where TRUE/FALSE needed")
        if name == "default":
            continue
        fn = _METHODS.get(name)
        if fn is not None:
            return index, fn, False
    fn = _METHODS.get("default")
    if fn is not None:
        return None, fn, True
    return None


def _no_method(classes):
    if len(classes) == 1:
        shown = '"' + classes[0] + '"'
    else:
        inner = ", ".join("'" + name + "'" for name in classes)
        shown = '"c(' + inner + ')"'
    return (
        "no applicable method for 'intersect' applied to an object of class " + shown
    )


def _show(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, str):
        return '"' + value + '"'
    return str(value)


def _unused(pos, kw):
    parts = [_show(value) for value in pos]
    parts.extend(f"{key} = {_show(value)}" for key, value in kw.items())
    if len(parts) == 1:
        return f"unused argument ({parts[0]})"
    return f"unused arguments ({', '.join(parts)})"


def _invoke(fn, x, y, pos, kw):
    signature = inspect.signature(fn)
    try:
        bound = signature.bind(x, y, *pos, **kw)
        return fn(*bound.args, **bound.kwargs)
    except TypeError:
        pass
    try:
        bound = signature.bind(x, *pos, **kw)
    except TypeError:
        extra = (() if missing(y) else (y,)) + pos
        raise IntersectError(_unused(extra, kw)) from None
    leftover = dict(kw)
    for name in bound.arguments:
        if name != "x":
            leftover.pop(name, None)
    extra_pos = () if missing(y) else (y,)
    if extra_pos or leftover:
        raise IntersectError(_unused(extra_pos, kw)) from None
    return fn(*bound.args, **bound.kwargs)


def _run(fn, frame):
    previous = getattr(_LOCAL, "frame", None)
    _LOCAL.frame = frame
    try:
        return _invoke(fn, frame.x, frame.y, frame.pos, frame.kw)
    finally:
        _LOCAL.frame = previous


def duplicate_x_error():
    """Raise R's duplicate-``x`` error (not expressible as a Python call)."""
    raise IntersectError('formal argument "x" matched by multiple actual arguments')


def duplicate_y_error():
    """Raise R's duplicate-``y`` error (not expressible as a Python call)."""
    raise IntersectError('formal argument "y" matched by multiple actual arguments')


def combine_errs(parts):
    """Combine proof ``errs`` the way R ``c`` and ``paste`` do."""
    return " || ".join(str(part) for part in parts)
