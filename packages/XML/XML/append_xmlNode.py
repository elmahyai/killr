"""append.xmlNode / append.XMLNode for internal libxml2 nodes."""

from __future__ import annotations

from typing import Any

from XML import addChildren
from XML import XMLInternalNode


def append_xmlNode(to: XMLInternalNode, *children: Any) -> XMLInternalNode:
    """Append child nodes and return the parent. A single list argument is unwrapped like R."""
    args: tuple[Any, ...] = children
    if len(args) == 1:
        first = args[0]
        if isinstance(first, list) and not isinstance(first, XMLInternalNode):
            args = tuple(first)
    addChildren(to, *args)
    return to
