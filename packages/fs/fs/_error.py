"""Errors raised by the fs translation."""


class FsError(Exception):
    """An fs condition. ``kind`` is the R class, such as ``invalid_argument``."""

    def __init__(self, message: str, kind: str = "invalid_argument"):
        super().__init__(message)
        self.kind = kind


def assert_ok(test: bool, message: str, kind: str = "invalid_argument") -> None:
    if not test:
        raise FsError(message, kind)


def assert_no_missing(values, name: str) -> None:
    missing = [index + 1 for index, value in enumerate(values) if value is None]
    if not missing:
        return
    shown = ", ".join(str(index) for index in missing[:12])
    if len(missing) > 12:
        shown += " and ..."
    raise FsError(
        f"`{name}` must not have missing values\n"
        f"  * NAs found at {len(missing)} locations: {shown}"
    )


def assert_recyclable(lengths: list[int]) -> None:
    if not lengths:
        return
    longest = max(lengths)
    for length in lengths:
        if length not in (0, 1, longest):
            raise FsError(
                "Arguments must have consistent lengths, "
                "only values of length one are recycled."
            )
