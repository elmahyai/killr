"""components from generics 0.1.4.

``components`` is ``UseMethod("components")``. The package imports methods, and a
normal R session already has that package on the search path, so the class
vector UseMethod walks is the one from that session:

- a double is ``double`` then ``numeric``
- an integer is ``integer`` then ``numeric``
- a matrix is ``matrix``, ``array``, then the vector class
- a 2-dimensional array is a matrix; a longer dim is ``array`` then the vector class
- an explicit class attribute is used as stored
- an S4 object also walks ``contains``

There is no default method in the package. A miss raises the standard
no-applicable-method error. ``NextMethod`` with nothing left to call raises
``no method to invoke``.

Argument matching follows the generic's formals ``object`` and ``...``.
An exact ``object`` wins over a prefix. Two prefixes are
``formal argument "object" matched by multiple actual arguments``.
When ``object`` is omitted and the call still has an argument, dispatch uses
that value's class and the method still sees ``object`` as missing.
``components()`` with no argument is class ``NULL``. ``components(object=MISSING)``
is an explicit empty argument: its class is ``name``, and ``object`` is still
missing.

A list or tuple of numbers is an atomic vector, the way ``c()`` is. ``List``
is an R list. ``Object`` carries an explicit class. ``Matrix`` and ``Array``
carry a dim.
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


class ComponentsError(Exception):
    """An R ``stop`` from ``UseMethod`` or from the matched method."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Object:
    """An R object with an explicit class vector.

    ``s4=True`` walks ``register_s4`` contains after the class name. An S3
    object leaves ``s4`` false, so a registered superclass is not consulted.
    An empty class vector means the value has no class attribute.
    """

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
    def __init__(self, classes, index, on_default, obj, pos, kw):
        self.classes = classes
        self.index = index
        self.on_default = on_default
        self.obj = obj
        self.pos = pos
        self.kw = kw


def missing(value):
    """R ``missing``. True when the argument was not supplied or was empty."""
    return value is MISSING


def force(value):
    """R ``force``. Evaluating a missing argument is an error."""
    if value is MISSING:
        raise ComponentsError('argument "object" is missing, with no default')
    return value


def register(class_name, fn):
    """Register ``components.<class_name>``. ``default`` is the fallback only."""
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
    """R ``NextMethod``. The original arguments are matched again.

    ``generic`` may be omitted or ``"components"``. A search that finds neither
    a later class nor ``components.default`` raises ``no method to invoke``.
    """
    del generic
    frame = getattr(_LOCAL, "frame", None)
    if frame is None or frame.on_default:
        raise ComponentsError("no method to invoke")
    for index in range(frame.index + 1, len(frame.classes)):
        name = frame.classes[index]
        if name is None:
            raise ComponentsError("missing value where TRUE/FALSE needed")
        if name == "default":
            continue
        fn = _METHODS.get(name)
        if fn is not None:
            nxt = _Frame(frame.classes, index, False, frame.obj, frame.pos, frame.kw)
            return _run(fn, nxt)
    fn = _METHODS.get("default")
    if fn is not None:
        nxt = _Frame(frame.classes, len(frame.classes), True, frame.obj, frame.pos, frame.kw)
        return _run(fn, nxt)
    raise ComponentsError("no method to invoke")


def components(*args, **kwargs):
    """Dispatch ``components`` on the class of ``object``.

    Extra positional arguments and unknown names go to ``...``. A prefix of
    ``object`` matches that formal when the exact name is absent.
    """
    obj, pos, kw, explicit, omitted = _bind(args, kwargs)
    if omitted:
        if pos:
            dispatch = pos[0]
        elif kw:
            dispatch = next(iter(kw.values()))
        else:
            dispatch = None
        passed = MISSING
        classes = _classes_of(dispatch)
    elif explicit:
        # components(object = ) is a missing symbol. Its class is "name",
        # and the method still sees object as missing. components() with no
        # argument at all is class NULL instead.
        passed = MISSING
        classes = ("name",)
    else:
        dispatch = obj
        passed = obj
        classes = _classes_of(dispatch)
    found = _resolve(classes)
    if found is None:
        raise ComponentsError(_no_method(classes))
    index, fn, on_default = found
    frame = _Frame(classes, 0 if index is None else index, on_default, passed, pos, dict(kw))
    return _run(fn, frame)


def _bind(args, kwargs):
    exact = [key for key in kwargs if key == "object"]
    partial = [
        key for key in kwargs if key and key != "object" and "object".startswith(key)
    ]
    if len(exact) > 1 or (not exact and len(partial) > 1):
        raise ComponentsError(
            'formal argument "object" matched by multiple actual arguments'
        )
    obj_key = exact[0] if exact else (partial[0] if partial else None)
    dots = {key: value for key, value in kwargs.items() if key != obj_key}
    if obj_key is not None:
        obj = kwargs[obj_key]
        return obj, tuple(args), dots, obj is MISSING, False
    if args:
        return args[0], tuple(args[1:]), dots, args[0] is MISSING, False
    return MISSING, (), dots, False, True


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
            raise ComponentsError("missing value where TRUE/FALSE needed")
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
        "no applicable method for 'components' applied to an object of class " + shown
    )


def _show(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _unused(pos, kw):
    parts = [_show(value) for value in pos]
    parts.extend(f"{key} = {_show(value)}" for key, value in kw.items())
    if len(parts) == 1:
        return f"unused argument ({parts[0]})"
    return f"unused arguments ({', '.join(parts)})"


def _invoke(fn, obj, pos, kw):
    signature = inspect.signature(fn)
    try:
        bound = signature.bind(obj, *pos, **kw)
    except TypeError:
        if not pos and not kw:
            raise
        raise ComponentsError(_unused(pos, kw)) from None
    return fn(*bound.args, **bound.kwargs)


def _run(fn, frame):
    previous = getattr(_LOCAL, "frame", None)
    _LOCAL.frame = frame
    try:
        return _invoke(fn, frame.obj, frame.pos, frame.kw)
    finally:
        _LOCAL.frame = previous
