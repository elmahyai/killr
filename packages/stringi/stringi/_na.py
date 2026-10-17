"""R's character missing value.

The string ``"NA"`` is a real string. An empty string is empty.
A missing character is this object.
"""


class NAType:
    def __repr__(self) -> str:
        return "NA"

    def __str__(self) -> str:
        return "NA"

    def __eq__(self, other: object) -> bool:
        return other is NA

    def __hash__(self) -> int:
        return id(NAType)


NA = NAType()


def is_na(value: object) -> bool:
    return value is NA
