"""endElement.SAX generic and the SAXState default method."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from XML.comment_SAX import SAXState

_end_element_methods: dict[type, Callable[..., Any]] = {}


def setMethod_endElement_SAX(state_type: type, handler: Callable[..., Any]) -> None:
    """Register an endElement.SAX method for ``state_type``, like R's setMethod."""
    _end_element_methods[state_type] = handler


def endElement_SAX(name: str, _state: SAXState | None = None) -> Any:
    """SAX end-element callback; the default SAXState method returns ``_state`` unchanged."""
    if _state is None:
        raise TypeError("invalid call in method dispatch to 'endElement.SAX' (no default method)")
    for cls in type(_state).__mro__:
        if cls in _end_element_methods:
            return _end_element_methods[cls](name, _state)
        if cls is SAXState:
            return _state
    raise TypeError("invalid call in method dispatch to 'endElement.SAX' (no default method)")
