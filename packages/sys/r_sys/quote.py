"""Windows argument quoting, ported from libuv through the R source."""

import re


def windows_quote(args):
    """Quote each argument the way CreateProcess expects."""
    if args is None:
        return None
    if isinstance(args, str):
        args = [args]
    if not isinstance(args, (list, tuple)):
        raise TypeError("args must be a character vector")
    return [windows_quote_one(item) for item in args]


def windows_quote_one(text):
    if not isinstance(text, str):
        raise TypeError("args must be a character vector")
    if text == "":
        return '""'
    if re.search(r'[ \t"]', text) is None:
        return text
    if re.search(r'["\\]', text) is None:
        return f'"{text}"'
    text = re.sub(r'(\\*)"', lambda match: match.group(1) + match.group(1) + '\\"', text)
    text = re.sub(r"(\\+)$", lambda match: match.group(1) + match.group(1), text)
    return f'"{text}"'
