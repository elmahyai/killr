"""append.XMLNode for internal libxml2 nodes."""

from __future__ import annotations

from typing import Any

from XML import XMLInternalNode
from XML.append_xmlNode import append_xmlNode


def append_XMLNode(to: XMLInternalNode, *children: Any) -> XMLInternalNode:
    """Append child nodes and return the parent. A single list argument is unwrapped like R."""
    return append_xmlNode(to, *children)
