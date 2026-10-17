"""Translation of sass::font_link().

The stylesheet link is not fetched here. The R html dependency only writes the
<link> tag into the page head, so the returned object is a plain record.
"""

from ._sass_values import (
    SASS_VERSION,
    HtmlDep,
    font_dep_name,
    link_head,
    new_font_collection,
    quote_css_font_families,
)


def font_link(family, href):
    if not isinstance(family, str):
        raise TypeError("Font `family` definitions must be a character string (length 1).")
    dep = HtmlDep(
        name=font_dep_name(family),
        version=SASS_VERSION,
        kind="link",
        href=href,
        head=link_head(href),
    )
    return new_font_collection([family], [dep])
