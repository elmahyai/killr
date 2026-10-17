"""verbatim_logical: emit true/false instead of yes/no."""

from r_yaml.types import NA, NA_CHARACTER, Verbatim


def verbatim_logical(x):
    """Return true/false strings marked so as_yaml does not quote them."""
    values = list(x) if isinstance(x, (list, tuple)) else [x]
    rendered = []
    for value in values:
        if isinstance(value, NA):
            rendered.append(NA_CHARACTER)
        elif value:
            rendered.append("true")
        else:
            rendered.append("false")
    return Verbatim(rendered)
