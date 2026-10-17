"""Conditions, sources, plots, and the evaluation list."""

from __future__ import annotations


class NAType:
    def __repr__(self) -> str:
        return "NA"

    def __str__(self) -> str:
        return "NA"

    def __eq__(self, other) -> bool:
        return isinstance(other, NAType)


NA = NAType()


class Invisible:
    def __init__(self, value) -> None:
        self.value = value


class Condition(Exception):
    def __init__(self, message: str, call=None) -> None:
        super().__init__(message)
        self.message = message
        self.call = call
        self.calls = None


class Message(Condition):
    pass


class Warning(Condition):
    pass


class Error(Condition):
    pass


class Source:
    def __init__(self, src: str) -> None:
        self.src = src

    def __eq__(self, other) -> bool:
        return isinstance(other, Source) and self.src == other.src


class GraphicsCall:
    def __init__(self, name: str, **data) -> None:
        self.name = name
        self.data = {key: _freeze(value) for key, value in data.items()}

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, GraphicsCall)
            and self.name == other.name
            and self.data == other.data
        )

    def __repr__(self) -> str:
        return f"GraphicsCall({self.name!r})"


def _freeze(value):
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


class RecordedPlot:
    def __init__(self, display_list: list) -> None:
        self.dl = list(display_list)

    def __eq__(self, other) -> bool:
        return isinstance(other, RecordedPlot) and self.dl == other.dl


class Evaluation(list):
    def __str__(self) -> str:
        return format_evaluation(self)


class Vector:
    def __init__(self, data) -> None:
        self.data = list(data)

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"Vector({self.data!r})"


class Restart(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


def is_message(x) -> bool:
    return isinstance(x, Message)


def is_warning(x) -> bool:
    return isinstance(x, Warning)


def is_error(x) -> bool:
    return isinstance(x, Error)


def is_source(x) -> bool:
    return isinstance(x, Source)


def is_recordedplot(x) -> bool:
    return isinstance(x, RecordedPlot)


def output_type(x) -> str:
    if isinstance(x, str):
        return "text"
    if is_error(x):
        return "error"
    if is_warning(x):
        return "warning"
    if is_message(x):
        return "message"
    if is_recordedplot(x):
        return "plot"
    if is_source(x):
        return "source"
    classes = getattr(x, "classes", None)
    if classes and ("gg" in classes or "ggplot2::ggplot" in classes):
        return "gg"
    if isinstance(x, type):
        return x.__name__
    return type(x).__name__


def indent(x, by: str = "  ", drop_trailing_nl: bool = True) -> str:
    if drop_trailing_nl and x.endswith("\n"):
        x = x[:-1]
    return by + x.replace("\n", "\n" + by)


def format_condition(x) -> str:
    from evaluate.parse import deparse

    if isinstance(x, Message):
        message = x.message
        if message.endswith("\n"):
            message = message[:-1]
        return message
    if isinstance(x, Error):
        kind = "Error"
    elif isinstance(x, Warning):
        kind = "Warning"
    else:
        kind = "Condition"
    if x.call is None:
        header = f"{kind}:"
    else:
        header = f"{kind} in {deparse(x.call)}:"
    return f"{header}\n{x.message}"


def format_evaluation(x) -> str:
    lines = ["<evaluation>"]
    for component in x:
        kind = output_type(component)
        if kind == "source":
            lines.append("Source code: ")
            lines.append(indent(component.src))
        elif kind == "text":
            lines.append("Text output: ")
            lines.append(indent(component))
        elif kind in {"message", "warning", "error"}:
            lines.append("Condition: ")
            lines.append(indent(format_condition(component)))
        elif kind == "plot":
            dl = component.dl
            lines.append(f"Plot [{len(dl)}]:")
            for call in dl:
                lines.append(f"  <base> {call.name}()")
        else:
            lines.append("Other: ")
            lines.append(" " + repr(component))
    return "\n".join(lines)


def new_evaluation(items) -> Evaluation:
    return Evaluation(items)
