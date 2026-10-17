"""localeToCharset, osVersion, and packageVersion against R 4.5.0."""

import pytest

from utils.locale import UtilsError, localeToCharset, osVersion, packageVersion


def test_charset_guesses():
    assert localeToCharset("C") == "ASCII"
    assert localeToCharset("en_US.UTF-8") == ["UTF-8", "ISO8859-1"]
    assert localeToCharset("pl_PL.iso88592") == "ISO8859-2"
    assert localeToCharset("en_US.utf8@euro") == "ISO8859-1"
    assert localeToCharset("en_US") == "ISO8859-1"
    assert localeToCharset("xx_YY") is None
    assert localeToCharset("ja_JP.eucjp") == "EUC-JP"


def test_os_and_package_version():
    assert osVersion() == "Debian GNU/Linux 13 (trixie)"
    assert packageVersion("utils") == "4.5.0"
    with pytest.raises(UtilsError, match="there is no package called ‘no-such-pkg’"):
        packageVersion("no-such-pkg")
