"""Font Awesome legacy ``<i>`` tags."""

from __future__ import annotations

import re

from .fa import _ICONS, _index
from .fa_html_dependency import fa_html_dependency


def fa_i(name: str, class_=None, *args, prefer_type="regular",
         html_dependency=None, **kwargs) -> str:
    """Return a Font Awesome ``<i>`` element as HTML."""
    if not isinstance(name, str):
        raise ValueError("A character vector should be supplied for `name`.")
    if re.fullmatch(r"^fa[a-z] fa-[a-z-]+$", name):
        icon_class = " ".join([name] + ([class_] if class_ is not None else []))
    else:
        idx = _index(name, prefer_type, fail=False)
        if idx is None:
            icon_class = f"fa{prefer_type[0]} fa-{name}"
            aria_name = name
        else:
            name = icon_class = _ICONS[idx]["full_name"]
            aria_name = name
        if idx is not None and class_ is not None:
            icon_class = f"{name} {class_}"
    aria_name = re.sub(r"^fa[a-z]* fa-", "", name)
    return f'<i class="{icon_class}" role="presentation" aria-label="{aria_name} icon"></i>'
