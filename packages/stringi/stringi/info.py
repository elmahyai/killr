"""stringi's ICU and charset summary.

``stri_info`` reports ICU 76 and Unicode 16 when that is the linked
library. The native charset block is the UTF-8 converter stringi 1.8.9
returns while ``U_CHARSET_IS_UTF8`` is set, which is this host. A missing
logical in that block is ``stringi._na.NA``.
"""

from __future__ import annotations

import icu

from stringi._na import NA
from stringi.locale import stri_locale_info

_VERSION = "1.8.9"

# ucnv_getStandard / ucnv_getStandardName for the UTF-8 converter, and
# ucnv_getMinCharSize / ucnv_getMaxCharSize. Unicode.1to1 is NA because
# the converter is not a fixed 8-bit encoding. ASCII.subset is true.
_UTF8_NATIVE = {
    "Name.friendly": "UTF-8",
    "Name.ICU": "UTF-8",
    "Name.UTR22": NA,
    "Name.IBM": "ibm-1208",
    "Name.WINDOWS": "windows-65001",
    "Name.JAVA": "UTF-8",
    "Name.IANA": "UTF-8",
    "Name.MIME": "UTF-8",
    "ASCII.subset": True,
    "Unicode.1to1": NA,
    "CharSize.8bit": False,
    "CharSize.min": 1,
    "CharSize.max": 3,
}


def _require_short(short) -> bool:
    if isinstance(short, (list, tuple)):
        if len(short) != 1:
            raise ValueError("length(short) == 1 is not TRUE")
        short = short[0]
    if short is NA:
        raise ValueError("missing value where TRUE/FALSE needed")
    if not isinstance(short, bool):
        raise ValueError("is.logical(short) is not TRUE")
    return short


def stri_info(short=False):
    """Describe the ICU build and the current default locale.

    ``short=False`` returns a dictionary with the Unicode version, the ICU
    version, the current locale, the internal charsets, the native charset,
    and whether the library is the system ICU with ``U_CHARSET_IS_UTF8``.
    ``short=True`` returns one summary line. The package version in that
    line is stringi 1.8.9.
    """

    brief = _require_short(short)
    locale = stri_locale_info(None)
    charset = dict(_UTF8_NATIVE)
    info = {
        "Unicode.version": icu.UNICODE_VERSION,
        "ICU.version": icu.ICU_VERSION,
        "Locale": locale,
        "Charset.internal": ["UTF-8", "UTF-16"],
        "Charset.native": charset,
        "ICU.system": True,
        "ICU.UTF8": True,
    }
    if not brief:
        return info
    system = "system" if info["ICU.system"] else "bundle"
    utf8 = "#U_CHARSET_IS_UTF8" if info["ICU.UTF8"] else ""
    return (
        f"stringi_{_VERSION} ({locale['Name']}.{charset['Name.friendly']}; "
        f"ICU4C {info['ICU.version']} [{system}{utf8}]; "
        f"Unicode {info['Unicode.version']})"
    )
