"""Named gaps: R behaviour that is not translated, reported by name."""


class NamedGap(NotImplementedError):
    """Raised by a withr function whose R behaviour is a named gap."""


def gap(name: str, reason: str) -> None:
    raise NamedGap(f"withr.{name} is a named gap, not translated: {reason}")


def stub(name: str, reason: str):
    """Build a function with the R name that raises the named gap."""

    def named_gap(*args, **kwargs):
        gap(name, reason)

    named_gap.__name__ = name
    named_gap.__qualname__ = name
    named_gap.__doc__ = f"Named gap: {reason}"
    return named_gap
