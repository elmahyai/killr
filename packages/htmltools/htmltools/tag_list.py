"""A list of tags, from htmltools 0.5.9.

``tagList`` is ``rlang::dots_list`` with class ``c("shiny.tag.list", "list")``.
Names are always stored. An unnamed element has the empty name. ``!!!`` is
``Splice``. A trailing comma is one ``EMPTY`` argument, and only that final
empty argument is dropped. ``Named`` places a name before a later positional
argument. ``.named``, ``.ignore_empty``, ``.preserve_empty``, ``.homonyms``,
and ``.check_assign`` are the dots_list controls and are not stored.
"""

from __future__ import annotations

import ast
import inspect
import warnings

from htmltools.escape import _character_double, is_na
from htmltools.html import _quote

_IGNORE = ("trailing", "none", "all")
_HOMONYMS = ("keep", "first", "last", "error")
_CONTROLS = (".named", ".ignore_empty", ".preserve_empty", ".homonyms", ".check_assign")

_ASSIGN_WARNING = (
    "Using `<-` as argument is often a mistake.\n"
    "Do you need to use `=` to match an argument?\n"
    "\n"
    "If you really want to use `<-`, please wrap in braces:\n"
    "\n"
    "  # Bad:\n"
    "  fn(a <- 1)\n"
    "\n"
    "  # Good:\n"
    "  fn(a = 1)       # Match 1 to parameter `a`\n"
    "  fn({ a <- 1 })  # Assign 1 to variable `a`"
)

_TREES: dict[str, ast.AST | None] = {}
_CALLS: dict[tuple[str, int], list[ast.Call]] = {}


class Empty:
    """One empty argument, as in R's ``tagList("hi",)``."""

    def __repr__(self) -> str:
        return "EMPTY"


EMPTY = Empty()


class MissingSymbol:
    """The missing symbol kept when ``.preserve_empty`` is true."""

    def __repr__(self) -> str:
        return "<missing>"


class Named:
    """A named dots element that is not the last argument.

    Python keywords have to follow positionals, so ``tagList(Named("a", 1), "b")``
    is R's ``tagList(a = 1, "b")``.
    """

    def __init__(self, name: str, value):
        self.name = "" if name is None else str(name)
        self.value = value


class Splice:
    """The Python form of rlang ``!!!``.

    ``None`` splices nothing. A ``TagList`` or a dict keeps its names. A
    list splices one element per item, unnamed unless ``names`` is given.
    """

    def __init__(self, values, names=None):
        if values is None:
            self.values = []
            self.names = []
            return
        if isinstance(values, TagList):
            self.values = list(values)
            self.names = list(values.names)
            return
        if isinstance(values, dict):
            self.names = ["" if key is None else str(key) for key in values.keys()]
            self.values = list(values.values())
            return
        if isinstance(values, Splice):
            self.values = list(values.values)
            self.names = list(values.names)
            return
        self.values = list(values)
        if names is None:
            self.names = [""] * len(self.values)
        else:
            if len(names) != len(self.values):
                raise ValueError("splice names must match the values")
            self.names = ["" if name is None else str(name) for name in names]


class TagList(list):
    """A list with class ``c("shiny.tag.list", "list")``."""

    def __init__(self, items, names):
        super().__init__(items)
        self.names = list(names)
        self.r_class = ("shiny.tag.list", "list")

    def __repr__(self) -> str:
        body = ", ".join(
            repr(value) if name == "" else f"{name}={value!r}"
            for name, value in zip(self.names, self)
        )
        return f"tagList({body})"


def _r_type(value) -> str:
    if value is None:
        return "NULL"
    if is_na(value) or isinstance(value, bool):
        return "logical"
    if isinstance(value, str):
        return "character"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "double"
    if isinstance(value, complex):
        return "complex"
    if isinstance(value, (list, tuple, dict)):
        return "list"
    return type(value).__name__


def _logical_flag(value) -> bool:
    """First element of a logical, with R's C truthiness.

    ``LOGICAL()`` rejects every other type. A logical ``NA`` is not zero,
    so it selects the true branch. An empty logical is not represented here.
    """

    if isinstance(value, bool):
        return value
    if is_na(value):
        return True
    if isinstance(value, (list, tuple)) and value and all(
        isinstance(item, bool) or is_na(item) for item in value
    ):
        first = value[0]
        if is_na(first):
            return True
        return bool(first)
    kind = _r_type(value)
    raise ValueError(f"LOGICAL() can only be applied to a 'logical', not a '{kind}'")


def _named_flag(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if (
        isinstance(value, (list, tuple))
        and len(value) == 1
        and isinstance(value[0], bool)
    ):
        return bool(value[0])
    raise ValueError("`.named` must be a logical value.")


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            cost = 0 if left_char == right_char else 1
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + cost)
            )
        previous = current
    return previous[-1]


def _pmatch(arg: str, choices: tuple[str, ...]):
    exact = [i for i, choice in enumerate(choices) if choice == arg]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    partial = [i for i, choice in enumerate(choices) if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    return None


def _suggest(arg: str, choices: tuple[str, ...]):
    candidate = None
    index = _pmatch(arg, choices)
    if index is not None:
        candidate = choices[index]
    ratios = [
        _levenshtein(arg, choice) / len(choice) if choice else 1.0 for choice in choices
    ]
    if any(ratio <= 0.5 for ratio in ratios):
        candidate = choices[min(range(len(ratios)), key=lambda i: (ratios[i], i))]
    if candidate is None:
        folded = [
            _levenshtein(arg.lower(), choice.lower()) / len(choice) if choice else 1.0
            for choice in choices
        ]
        if any(ratio <= 0.5 for ratio in folded):
            candidate = choices[min(range(len(folded)), key=lambda i: (folded[i], i))]
    return candidate


def _oxford(items: list[str], conjunction: str) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return ", ".join(items[:-1]) + f", {conjunction} " + items[-1]


def _invalid_choice(arg: str, choices: tuple[str, ...], error_arg: str) -> str:
    series = _oxford([f'"{choice}"' for choice in choices], "or")
    message = f'`{error_arg}` must be one of {series}, not "{arg}".'
    candidate = _suggest(arg, choices)
    if candidate is not None:
        message += f'\n\u2139 Did you mean "{candidate}"?'
    return message


def _match_choice(value, choices: tuple[str, ...], error_arg: str) -> str:
    if isinstance(value, str):
        if value in choices:
            return value
        raise ValueError(_invalid_choice(value, choices, error_arg))
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        if len(value) == 1 and value[0] in choices:
            return value[0]
        raise ValueError("`arg` must be a string or have the same length as `values`.")
    raise ValueError("`arg` must be a string or have the same length as `values`.")


def _func_name(node: ast.AST):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _calls_on_line(filename: str, lineno: int) -> list[ast.Call]:
    key = (filename, lineno)
    cached = _CALLS.get(key)
    if cached is not None:
        return cached
    if filename not in _TREES:
        try:
            with open(filename, encoding="utf-8") as handle:
                source = handle.read()
        except OSError:
            _TREES[filename] = None
        else:
            _TREES[filename] = ast.parse(source)
    tree = _TREES[filename]
    found: list[ast.Call] = []
    if tree is not None:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and _func_name(node.func) == "tagList"
                and node.lineno == lineno
            ):
                found.append(node)
    _CALLS[key] = found
    return found


def _expressions_from_caller(count: int):
    caller = inspect.currentframe().f_back.f_back
    nodes = _calls_on_line(caller.f_code.co_filename, caller.f_lineno)
    if len(nodes) != 1:
        return None
    call = nodes[0]
    if any(isinstance(arg, ast.Starred) for arg in call.args):
        return None
    if len(call.args) != count:
        return None
    return call.args


def deparse_constant(value) -> str:
    """``as_label`` of one spliced value, and ``deparse`` of one literal."""

    if value is None:
        return "NULL"
    if is_na(value):
        return "NA"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, int):
        return str(value) + "L"
    if isinstance(value, float):
        return _character_double(value)
    return str(value)


def deparse_expr(node: ast.AST) -> str:
    """R ``deparse`` of a small Python argument expression."""

    if isinstance(node, ast.Constant):
        return deparse_constant(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return "-" + deparse_expr(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
    ):
        symbol = {ast.Add: " + ", ast.Sub: " - ", ast.Mult: " * ", ast.Div: " / "}[
            type(node.op)
        ]
        return deparse_expr(node.left) + symbol + deparse_expr(node.right)
    if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
        return node.target.id + " <- " + deparse_expr(node.value)
    return ast.unparse(node)


def _is_splice(value) -> bool:
    return isinstance(value, Splice) or type(value).__name__ == "Splice"


def _splice_pairs(value):
    if isinstance(value, Splice):
        return list(zip(value.names, value.values))
    if value is None:
        return []
    names = getattr(value, "names", None)
    values = list(value.values) if hasattr(value, "values") else list(value)
    if names is None:
        names = [""] * len(values)
    return list(zip(names, values))


def _homonym_message(groups: list[tuple[str, list[int]]]) -> str:
    lines = ["Arguments in `...` must have unique names."]
    for name, positions in groups:
        shown = _oxford([str(pos) for pos in positions], "and")
        lines.append(
            f"\u2716 Multiple arguments named `{name}` at positions {shown}."
        )
    return "\n".join(lines)


def _apply_homonyms(items: list[tuple[str, object]], how: str):
    if how == "keep":
        return items
    if how == "error":
        seen: dict[str, list[int]] = {}
        for index, (name, _value) in enumerate(items, 1):
            if name == "":
                continue
            seen.setdefault(name, []).append(index)
        groups = [(name, positions) for name, positions in seen.items() if len(positions) > 1]
        if groups:
            raise ValueError(_homonym_message(groups))
        return items
    if how == "first":
        seen_names: set[str] = set()
        kept = []
        for name, value in items:
            if name != "" and name in seen_names:
                continue
            kept.append((name, value))
            if name != "":
                seen_names.add(name)
        return kept
    seen_names = set()
    keep = [False] * len(items)
    for index in range(len(items) - 1, -1, -1):
        name = items[index][0]
        if name == "" or name not in seen_names:
            keep[index] = True
            if name != "":
                seen_names.add(name)
    return [item for item, flag in zip(items, keep) if flag]


def tagList(*args, **kwargs):
    """Collect ``...`` into a ``shiny.tag.list``.

    Positional arguments stay in order. Keywords follow them. ``EMPTY`` is an
    empty argument. ``Splice`` is ``!!!``. ``Named`` is a name that sits before
    another positional. With the defaults, one trailing ``EMPTY`` is dropped
    and any other empty argument is an error. ``.preserve_empty`` true keeps
    that argument as the missing symbol. ``.homonyms`` is ``keep``, ``first``,
    ``last``, or ``error``. ``.named`` true names an unnamed argument from its
    expression, and a spliced element from ``as_label``. ``.check_assign`` true
    warns when an argument is an assignment.
    """

    controls = {key: kwargs.pop(key) for key in _CONTROLS if key in kwargs}
    named_flag = _named_flag(controls[".named"]) if ".named" in controls else False
    ignore = (
        _match_choice(controls[".ignore_empty"], _IGNORE, ".ignore_empty")
        if ".ignore_empty" in controls
        else "trailing"
    )
    preserve = (
        _logical_flag(controls[".preserve_empty"])
        if ".preserve_empty" in controls
        else False
    )
    homonyms = (
        _match_choice(controls[".homonyms"], _HOMONYMS, ".homonyms")
        if ".homonyms" in controls
        else "keep"
    )
    check_assign = (
        _logical_flag(controls[".check_assign"])
        if ".check_assign" in controls
        else False
    )

    expressions = None
    if args and (named_flag or check_assign):
        expressions = _expressions_from_caller(len(args))

    raw = []
    for index, value in enumerate(args, 1):
        expr = expressions[index - 1] if expressions is not None else None
        if check_assign and isinstance(expr, ast.NamedExpr):
            warnings.warn(_ASSIGN_WARNING, stacklevel=2)
        if value is EMPTY or isinstance(value, Empty):
            raw.append(("empty", index, "", None))
        elif isinstance(value, Named):
            raw.append(("value", index, value.name, value.value, expr))
        elif _is_splice(value):
            raw.append(("splice", index, value))
        else:
            raw.append(("value", index, "", value, expr))
    for key, value in kwargs.items():
        raw.append(("value", None, str(key), value, None))

    if ignore == "trailing" and len(raw) >= 2 and raw[-1][0] == "empty":
        raw = raw[:-1]
    if ignore == "all":
        raw = [item for item in raw if item[0] != "empty"]

    items: list[tuple[str, object]] = []
    for entry in raw:
        kind = entry[0]
        if kind == "empty":
            if not preserve:
                raise ValueError(f"Argument {entry[1]} can't be empty.")
            items.append(("", MissingSymbol()))
            continue
        if kind == "splice":
            for name, value in _splice_pairs(entry[2]):
                shown = "" if name is None else str(name)
                if named_flag and shown == "":
                    shown = deparse_constant(value)
                items.append((shown, value))
            continue
        _kind, _index, name, value, expr = entry
        shown = name
        if named_flag and shown == "":
            shown = deparse_expr(expr) if expr is not None else deparse_constant(value)
        items.append((shown, value))

    items = _apply_homonyms(items, homonyms)
    names = [name for name, _value in items]
    values = [value for _name, value in items]
    return TagList(values, names)
