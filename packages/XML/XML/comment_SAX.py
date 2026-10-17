"""comment.SAX generic and the SAXState default method."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_comment_methods: dict[type, Callable[..., Any]] = {}


class SAXState:
    """Virtual base for SAX parser state passed to xmlEventParse handlers."""

    def __init__(self) -> None:
        if type(self) is SAXState:
            raise TypeError('trying to generate an object from a virtual class ("SAXState")')


def setMethod_comment_SAX(state_type: type, handler: Callable[..., Any]) -> None:
    """Register a comment.SAX method for ``state_type``, like R's setMethod."""
    _comment_methods[state_type] = handler


def comment_SAX(content: str, _state: SAXState | None = None) -> Any:
    """SAX comment callback; the default SAXState method returns ``_state`` unchanged."""
    if _state is None:
        raise TypeError("invalid call in method dispatch to 'comment.SAX' (no default method)")
    for cls in type(_state).__mro__:
        if cls in _comment_methods:
            return _comment_methods[cls](content, _state)
        if cls is SAXState:
            return _state
    raise TypeError("invalid call in method dispatch to 'comment.SAX' (no default method)")
