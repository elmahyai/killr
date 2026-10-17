"""assert_that, see_if, and validate_that."""

from __future__ import annotations

import inspect
from typing import Any

import assertthat.base  # register base predicates before messages

from assertthat.expr import (
    BUILTINS,
    Call,
    Infix,
    Matched,
    evaluate,
    fail_default,
    lookup,
    match_call,
    parse,
    render,
)
from assertthat.failure import on_failure
from assertthat.objects import NA, Vector, elements, is_logical, is_missing, length

BASE_FS: dict[str, Any] = {}


class AssertThatError(Exception):
    """The condition see_if catches. check_result uses ValueError instead."""


class SeeResult:
    def __init__(self, value: bool, msg: str | None = None) -> None:
        self.value = value
        self.msg = msg

    def __bool__(self) -> bool:
        return self.value is True

    def __repr__(self) -> str:
        if self.msg is None:
            return "[1] TRUE" if self.value else "[1] FALSE"
        shown = self.msg.replace("\\", "\\\\").replace('"', '\\"')
        return f'[1] FALSE\nattr(,"msg")\n[1] "{shown}"'

    def __str__(self) -> str:
        return repr(self)


def _caller_env() -> dict[str, Any]:
    frame = inspect.currentframe()
    assert frame is not None and frame.f_back is not None and frame.f_back.f_back is not None
    return dict(frame.f_back.f_back.f_locals)


def check_result(value: Any) -> None:
    if isinstance(value, SeeResult):
        value = value.value
    if isinstance(value, Vector):
        if value.mode != "logical":
            raise ValueError("assert_that: assertion must return a logical value")
        if len(value.data) != 1:
            raise ValueError("assert_that: length of assertion is not 1")
        if any(is_missing(item) for item in value.data):
            raise ValueError("assert_that: missing values present in assertion")
        return
    if not is_logical(value) or isinstance(value, Vector):
        raise ValueError("assert_that: assertion must return a logical value")
    if is_missing(value):
        raise ValueError("assert_that: missing values present in assertion")
    if length(value) != 1:
        raise ValueError("assert_that: length of assertion is not 1")


def _logical(value: Any) -> bool:
    if isinstance(value, SeeResult):
        return value.value
    if isinstance(value, Vector):
        return value.data[0] is True
    return value is True


def _prepare(assertion: Any) -> Any:
    if isinstance(assertion, str):
        return parse(assertion)
    if assertion is True:
        return parse("TRUE")
    if assertion is False:
        return parse("FALSE")
    raise TypeError("assertion must be an expression string or a single logical value")


def get_message(res: Any, node: Any, env: dict[str, Any]) -> str:
    if isinstance(res, SeeResult) and res.msg is not None:
        return res.msg
    if isinstance(node, (Call, Infix)):
        if isinstance(node, Call):
            function = evaluate(node.fn, env)
            fname = node.fn.value
        else:
            function = lookup(node.op, env)
            fname = node.op
        matched = match_call(function, node)
        handler = on_failure(function) or BASE_FS.get(fname) or fail_default
        return handler(matched, env)
    return fail_default(node, env)


def see_if(*assertions: Any, env: dict[str, Any] | None = None, msg: str | None = None) -> SeeResult:
    if env is None:
        env = _caller_env()
    last = True
    for assertion in assertions:
        node = _prepare(assertion)
        try:
            last = evaluate(node, env)
        except AssertThatError as error:
            return SeeResult(False, error.args[0])
        check_result(last)
        if not _logical(last):
            if msg is None:
                msg = get_message(last, node, env)
            return SeeResult(False, msg)
    return SeeResult(True)


def assert_that(*assertions: Any, env: dict[str, Any] | None = None, msg: str | None = None) -> bool:
    if env is None:
        env = _caller_env()
    result = see_if(*assertions, env=env, msg=msg)
    if result:
        return True
    raise AssertThatError(result.msg)


def validate_that(*assertions: Any, env: dict[str, Any] | None = None, msg: str | None = None) -> bool | str:
    if env is None:
        env = _caller_env()
    result = see_if(*assertions, env=env, msg=msg)
    if result:
        return True
    return result.msg or ""


def _deparse_one(node: Any) -> str:
    from assertthat.expr import deparse_lines

    if node is None:
        return "NULL"
    return "".join(deparse_lines(node))


def _is_not(thing: str):
    def fail(call: Matched, env: dict[str, Any]) -> str:
        del env
        return f"{_deparse_one(call[2])} is not {thing}"

    return fail


def _logical_is_not(failed: str):
    def fail(call: Matched, env: dict[str, Any]) -> str:
        del env
        left = _deparse_one(call[2])
        right = _deparse_one(call[3])
        return f"{left} not {failed} {right}"

    return fail


def _and_message(call: Matched, env: dict[str, Any]) -> str:
    left = evaluate(call[2], env)
    if not left:
        return get_message(left, call[2], env)
    right = evaluate(call[3], env)
    return get_message(right, call[3], env)


def _or_message(call: Matched, env: dict[str, Any]) -> str:
    left = evaluate(call[2], env)
    right = evaluate(call[3], env)
    return get_message(left, call[2], env) + " or " + get_message(right, call[3], env)


def _any_message(call: Matched, env: dict[str, Any]) -> str:
    del env
    return f"No elements of {_deparse_one(call[2])} are true"


def _all_message(call: Matched, env: dict[str, Any]) -> str:
    res = evaluate(call[2], env)
    indexes: list[Any] = []
    for position, item in enumerate(elements(res), start=1):
        if item is False:
            indexes.append(position)
    if len(indexes) > 10:
        indexes = indexes[:5] + ["..."]
    shown = ", ".join(str(item) for item in indexes)
    return f"Elements {shown} of {_deparse_one(call[2])} are not true"


def _file_exists_message(call: Matched, env: dict[str, Any]) -> str:
    path = evaluate(call[2], env)
    return f"Path '{path}' does not exist"


def _any_duplicated_message(call: Matched, env: dict[str, Any]) -> str:
    del env
    target = call["x"]
    return f"{render(target) if target is not None else 'NULL'} is not unique"


def _identical_message(call: Matched, env: dict[str, Any]) -> str:
    del env
    left = call["x"]
    right = call["y"]
    return f"{_deparse_one(left)} not identical to {_deparse_one(right)}"


def _inherits_message(call: Matched, env: dict[str, Any]) -> str:
    class_name = evaluate(call["what"], env)
    return f"{_deparse_one(call['x'])} does not inherit from class {class_name}"


def install_messages() -> None:
    pairs = {
        "is.atomic": "an atomic vector",
        "is.character": "a character vector",
        "is.complex": "a complex vector",
        "is.double": "a numeric vector",
        "is.integer": "an integer vector",
        "is.numeric": "a numeric or integer vector",
        "is.raw": "a raw vector",
        "is.vector": "an atomic vector without attributes",
        "is.factor": "a factor",
        "is.ordered": "an ordered factor",
        "is.array": "an array",
        "is.data.frame": "a data frame",
        "is.list": "a list",
        "is.matrix": "a matrix",
        "is.null": "NULL",
        "is.environment": "an environment",
        "is.function": "a function",
        "is.primitive": "a primitive function",
        "is.call": "a quoted call",
        "is.expression": "an expression object",
        "is.name": "a name",
        "is.pairlist": "a pairlist",
        "is.recursive": "a recursive object",
        "is.symbol": "a name",
    }
    for name, thing in pairs.items():
        BASE_FS[name] = _is_not(thing)
        if name not in BUILTINS:
            def _missing(x: Any = None, _name: str = name) -> bool:
                del x, _name
                return False

            from assertthat.expr import register

            register(name, _missing, ["x"], primitive=True)
    BASE_FS["inherits"] = _inherits_message
    BASE_FS["=="] = _logical_is_not("equal to")
    BASE_FS["<"] = _logical_is_not("less than")
    BASE_FS[">"] = _logical_is_not("greater than")
    BASE_FS[">="] = _logical_is_not("greater than or equal to")
    BASE_FS["<="] = _logical_is_not("less than or equal to")
    BASE_FS["!="] = _logical_is_not("not equal to")
    BASE_FS["&&"] = _and_message
    BASE_FS["||"] = _or_message
    BASE_FS["any"] = _any_message
    BASE_FS["all"] = _all_message
    BASE_FS["file.exists"] = _file_exists_message
    BASE_FS["anyDuplicated"] = _any_duplicated_message
    BASE_FS["identical"] = _identical_message


install_messages()
