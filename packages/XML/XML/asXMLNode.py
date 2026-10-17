"""asXMLNode: coerce values to the R list-shaped XMLNode tree."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

_XML_ENTITIES: Mapping[str, str] = {
    "&": "amp",
    ">": "gt",
    "<": "lt",
    "'": "apos",
    '"': "quot",
}


class XMLNamespaceDefinitions(list):
    """Placeholder for R's XMLNamespaceDefinitions."""


class _AsIs:
    """Marks text that must not receive entity escaping."""


class XMLNode:
    """R's list-shaped XMLNode / XMLTextNode object."""

    __slots__ = ("name", "attributes", "children", "child_names", "namespace", "namespace_definitions", "value", "classes")

    def __init__(
        self,
        name: str,
        *,
        attributes: dict[str, str] | None = None,
        children: Sequence[XMLNode] | None = None,
        child_names: Sequence[str] | None = None,
        namespace: str = "",
        namespace_definitions: XMLNamespaceDefinitions | None = None,
        value: str | None = None,
        classes: tuple[str, ...] = ("XMLNode",),
    ) -> None:
        self.name = name
        self.attributes = attributes
        self.children = list(children or ())
        self.child_names = list(child_names or ())
        if not self.child_names and self.children:
            self.child_names = [_xml_name(child) for child in self.children]
        self.namespace = namespace
        self.namespace_definitions = namespace_definitions or XMLNamespaceDefinitions()
        self.value = value
        self.classes = classes

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    @property
    def class_(self) -> tuple[str, ...]:
        return self.classes


def _insert_entities(value: str, entities: Mapping[str, str] = _XML_ENTITIES) -> str:
    for char, name in entities.items():
        value = value.replace(char, f"&{name};")
    return value


def _is_xml_node(x: Any) -> bool:
    return isinstance(x, XMLNode)


def xmlNode(
    name: str,
    *children: Any,
    attrs: dict[str, str] | None = None,
    namespace: str = "",
    namespace_definitions: XMLNamespaceDefinitions | None = None,
) -> XMLNode:
    """Minimal xmlNode for the list-shaped tree (used by asXMLNode checks)."""
    kids = [asXMLNode(child) for child in children]
    child_names = [_xml_name(child) for child in kids]
    return XMLNode(
        name=name,
        attributes=attrs,
        children=kids,
        child_names=child_names,
        namespace=namespace,
        namespace_definitions=namespace_definitions,
        classes=("XMLNode",),
    )


def xmlTextNode(
    value: Any,
    namespace: str = "",
    entities: Mapping[str, str] | None = _XML_ENTITIES,
    cdata: bool = False,
) -> XMLNode:
    """Build an XMLTextNode the way createNode.R does."""
    text = value if isinstance(value, str) else str(value)
    node = xmlNode("text", namespace=namespace)
    if entities and not isinstance(value, _AsIs):
        text = _insert_entities(text, entities)
    if cdata:
        raise NotImplementedError("xmlCDataNode is not translated")
    node.value = text
    classes: list[str] = ["XMLTextNode", "XMLNode"]
    if not cdata:
        node.classes = tuple(classes)
    if entities:
        node.classes = (*node.classes, "EntitiesEscaped")
    return node


def asXMLNode(x: Any) -> Any:
    """Coerce to an XMLNode, wrapping other values as XMLTextNode objects."""
    if not _is_xml_node(x):
        return xmlTextNode(x)
    return x


def _xml_name(node: XMLNode) -> str:
    """xmlName for list-shaped nodes."""
    return node.name
