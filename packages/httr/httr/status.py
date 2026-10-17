"""Extract an HTTP status code the way httr 1.4.9 does.

``status_code`` is an S3 generic. A response is a named list, and the
response method returns the ``status_code`` element with R's ``$`` rules.
A numeric value, including an integer, is returned unchanged. Nothing here
sends a request: the caller builds the response object.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext


class Missing:
    """R's NA. The vector's storage mode says integer or double."""

    def __repr__(self):
        return "NA"


MISSING = Missing()

# A name that is NA_character_. It does not match `$`.
NA_NAME = object()


class LogicalNA:
    """R's bare ``NA``, a length-1 logical missing value."""


class Response:
    """An R list. ``classes`` is the S3 class vector, response by default.

    ``fields`` keeps every pair, including duplicate names, an unnamed
    element (``None``), and an NA name (``NA_NAME``).
    """

    def __init__(self, fields, classes=("response",)):
        self.fields = [(name, value) for name, value in fields]
        self.classes = (classes,) if isinstance(classes, str) else tuple(classes)

    def __len__(self):
        return len(self.fields)


class Numeric:
    """An atomic vector. ``classes is None`` means the implicit S3 class.

    An explicit class vector replaces that implicit class, which is what
    ``structure(..., class =)`` does. ``kind`` is ``integer``, ``double``,
    or ``character``. A matrix or array is this vector plus ``dim``.
    """

    def __init__(
        self,
        values,
        kind="double",
        names=None,
        dim=None,
        dimnames=None,
        classes=None,
        comment=None,
    ):
        if kind not in ("integer", "double", "character"):
            raise ValueError("kind must be integer, double, or character")
        stored = []
        for value in values:
            if value is MISSING:
                stored.append(MISSING)
            elif kind == "double":
                stored.append(float(value))
            elif kind == "integer":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError("an integer vector holds ints")
                stored.append(value)
            else:
                if not isinstance(value, str):
                    raise TypeError("a character vector holds strings")
                stored.append(value)
        self.values = stored
        self.kind = kind
        self.names = None if names is None else tuple(names)
        self.dim = None if dim is None else tuple(dim)
        if dimnames is None:
            self.dimnames = None
        else:
            self.dimnames = tuple(
                None if margin is None else tuple(margin) for margin in dimnames
            )
        if classes is None:
            self.classes = None
        elif isinstance(classes, str):
            self.classes = (classes,)
        else:
            self.classes = tuple(classes)
        self.comment = comment

    def __len__(self):
        return len(self.values)

    def implicit_classes(self):
        if self.kind == "integer":
            tail = ("integer", "numeric")
        elif self.kind == "double":
            tail = ("double", "numeric")
        else:
            tail = (self.kind,)
        if not self.dim:
            return tail
        if len(self.dim) == 2:
            return ("matrix", "array", *tail)
        return ("array", *tail)


def status_code(x):
    """Return the status code on a response, or return a numeric value as it is.

    Dispatch follows R 4.5. An integer with no class attribute tries
    ``integer`` and then ``numeric``. A double tries ``double`` and then
    ``numeric``. A matrix or array tries those classes first. There is no
    default method.
    """
    classes = _dispatch_classes(x)
    for name in classes:
        if name == "response":
            return _from_response(x)
        if name == "numeric":
            return x
    raise ValueError(
        "no applicable method for 'status_code' applied to an object of class "
        + _class_phrase(classes)
    )


def _dispatch_classes(x):
    if x is None:
        return ("NULL",)
    if isinstance(x, (bool, LogicalNA)):
        return ("logical",)
    if isinstance(x, int):
        return ("integer", "numeric")
    if isinstance(x, float):
        return ("double", "numeric")
    if isinstance(x, str):
        return ("character",)
    if isinstance(x, list):
        return ("list",)
    if isinstance(x, Response):
        return x.classes if x.classes else ("list",)
    if isinstance(x, Numeric):
        if x.classes is not None:
            return x.classes
        return x.implicit_classes()
    raise TypeError("status_code does not know this object")


def _class_phrase(classes):
    if len(classes) == 1:
        return '"' + classes[0] + '"'
    inner = ", ".join("'" + name + "'" for name in classes)
    return '"c(' + inner + ')"'


def _from_response(x):
    if isinstance(x, Response):
        return _dollar(x.fields, "status_code")
    if x is None:
        return None
    raise ValueError("$ operator is invalid for atomic vectors")


def _dollar(fields, name):
    """R's `$`: the first exact name, otherwise one unique prefix.

    Several prefixes are NULL. A missing name and an NA name do not match.
    ``warnPartialMatchDollar`` is FALSE in a normal session, so the unique
    prefix is quiet.
    """
    partial = []
    for key, value in fields:
        if not isinstance(key, str):
            continue
        if key == name:
            return value
        if key.startswith(name):
            partial.append(value)
    if len(partial) == 1:
        return partial[0]
    return None


# The names are the character keys ``%in%`` and ``[[`` use. Code 424 is
# listed twice in the R source; ``[[`` keeps the first description.
_STATUS_PAIRS = (
    ("100", "Continue"),
    ("101", "Switching Protocols"),
    ("102", "Processing (WebDAV; RFC 2518)"),
    ("200", "OK"),
    ("201", "Created"),
    ("202", "Accepted"),
    ("203", "Non-Authoritative Information"),
    ("204", "No Content"),
    ("205", "Reset Content"),
    ("206", "Partial Content"),
    ("207", "Multi-Status (WebDAV; RFC 4918)"),
    ("208", "Already Reported (WebDAV; RFC 5842)"),
    ("226", "IM Used (RFC 3229)"),
    ("300", "Multiple Choices"),
    ("301", "Moved Permanently"),
    ("302", "Found"),
    ("303", "See Other"),
    ("304", "Not Modified"),
    ("305", "Use Proxy"),
    ("306", "Switch Proxy"),
    ("307", "Temporary Redirect"),
    ("308", "Permanent Redirect (experimental Internet-Draft)"),
    ("400", "Bad Request"),
    ("401", "Unauthorized"),
    ("402", "Payment Required"),
    ("403", "Forbidden"),
    ("404", "Not Found"),
    ("405", "Method Not Allowed"),
    ("406", "Not Acceptable"),
    ("407", "Proxy Authentication Required"),
    ("408", "Request Timeout"),
    ("409", "Conflict"),
    ("410", "Gone"),
    ("411", "Length Required"),
    ("412", "Precondition Failed"),
    ("413", "Request Entity Too Large"),
    ("414", "Request-URI Too Long"),
    ("415", "Unsupported Media Type"),
    ("416", "Requested Range Not Satisfiable"),
    ("417", "Expectation Failed"),
    ("418", "I'm a teapot (RFC 2324)"),
    ("420", "Enhance Your Calm (Twitter)"),
    ("422", "Unprocessable Entity (WebDAV; RFC 4918)"),
    ("423", "Locked (WebDAV; RFC 4918)"),
    ("424", "Failed Dependency (WebDAV; RFC 4918)"),
    ("424", "Method Failure (WebDAV)"),
    ("425", "Unordered Collection (Internet draft)"),
    ("426", "Upgrade Required (RFC 2817)"),
    ("428", "Precondition Required (RFC 6585)"),
    ("429", "Too Many Requests (RFC 6585)"),
    ("431", "Request Header Fields Too Large (RFC 6585)"),
    ("444", "No Response (Nginx)"),
    ("449", "Retry With (Microsoft)"),
    ("450", "Blocked by Windows Parental Controls (Microsoft)"),
    ("451", "Unavailable For Legal Reasons (Internet draft)"),
    ("499", "Client Closed Request (Nginx)"),
    ("500", "Internal Server Error"),
    ("501", "Not Implemented"),
    ("502", "Bad Gateway"),
    ("503", "Service Unavailable"),
    ("504", "Gateway Timeout"),
    ("505", "HTTP Version Not Supported"),
    ("506", "Variant Also Negotiates (RFC 2295)"),
    ("507", "Insufficient Storage (WebDAV; RFC 4918)"),
    ("508", "Loop Detected (WebDAV; RFC 5842)"),
    ("509", "Bandwidth Limit Exceeded (Apache bw/limited extension)"),
    ("510", "Not Extended (RFC 2774)"),
    ("511", "Network Authentication Required (RFC 6585)"),
    ("598", "Network read timeout error (Unknown)"),
    ("599", "Network connect timeout error (Unknown)"),
)

_REASONS = {}
for _code, _reason in _STATUS_PAIRS:
    if _code not in _REASONS:
        _REASONS[_code] = _reason

_STATUS_TYPES = (
    "Information",
    "Success",
    "Redirection",
    "Client error",
    "Server error",
)

_NONNUMERIC = object()
_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)


class HttpStatus:
    """The list ``http_status`` returns.

    Each component is the text of one length-1 character vector:
    ``category``, ``reason``, and ``message``.
    """

    def __init__(self, category, reason, message):
        self.category = category
        self.reason = reason
        self.message = message


def http_status(x):
    """Describe a known HTTP status code.

    ``status_code`` supplies the code. A response is the object the caller
    built; this function does not send a request. A code whose character
    form is not in the table is an error. The category is ``status %/% 100``
    into Information, Success, Redirection, Client error, or Server error.
    That division uses the numeric value, while the reason is looked up
    from ``as.character``, so a value that prints as 200 can still fall in
    the 100s. Code 424 keeps the first description.
    """
    status = status_code(x)
    size = _status_length(status)
    if size == 0:
        raise ValueError("argument is of length zero")
    if size > 1:
        raise ValueError("the condition has length > 1")
    text = _status_character(status)
    reason = _REASONS.get(text)
    if reason is None:
        raise ValueError("Unknown http status code: " + text)
    category = _status_type(_status_idiv100(status))
    message = category + ": (" + text + ") " + reason
    return HttpStatus(category, reason, message)


def _status_length(status):
    if status is None:
        return 0
    if isinstance(status, (bool, int, float, str, complex, LogicalNA)):
        return 1
    if isinstance(status, (list, Numeric)):
        return len(status)
    raise TypeError("http_status does not know this object")


def _status_character(status):
    if isinstance(status, Numeric):
        value = status.values[0]
        if status.kind == "character":
            return value
        if value is MISSING:
            return "NA"
        if status.kind == "integer":
            return _character_integer(value)
        return _character_double(value)
    if isinstance(status, list):
        return _scalar_character(status[0])
    return _scalar_character(status)


def _scalar_character(value):
    if value is None:
        return "NULL"
    if value is MISSING or isinstance(value, LogicalNA):
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return _character_integer(value)
    if isinstance(value, float):
        return _character_double(value)
    if isinstance(value, str):
        return value
    if isinstance(value, complex):
        return _character_complex(value)
    raise TypeError("http_status does not know this object")


def _status_idiv100(status):
    number = _status_number(status)
    if number is _NONNUMERIC:
        raise ValueError("non-numeric argument to binary operator")
    quotient = number / 100.0
    if math.isnan(quotient) or math.isinf(quotient):
        return quotient
    return math.floor(quotient)


def _status_number(status):
    if isinstance(status, bool):
        return float(status)
    if isinstance(status, int):
        return float(status)
    if isinstance(status, float):
        return status
    if isinstance(status, Numeric) and status.kind in ("integer", "double"):
        value = status.values[0]
        if value is MISSING:
            return float("nan")
        return float(value)
    return _NONNUMERIC


def _status_type(bucket):
    if isinstance(bucket, float) and (math.isnan(bucket) or math.isinf(bucket)):
        raise ValueError("subscript out of bounds")
    index = math.trunc(bucket)
    if index == 0:
        raise ValueError(
            "attempt to select less than one element in get1index <real>"
        )
    if index < 0:
        raise ValueError("invalid negative subscript in get1index <real>")
    if index > len(_STATUS_TYPES):
        raise ValueError("subscript out of bounds")
    return _STATUS_TYPES[index - 1]


def _character_integer(value):
    if -2147483647 <= value <= 2147483647:
        return str(value)
    return _character_double(float(value))


def _character_complex(value):
    real = _character_double(value.real)
    imag = value.imag
    if math.copysign(1.0, imag) < 0.0:
        return real + "-" + _character_double(abs(imag)) + "i"
    return real + "+" + _character_double(imag) + "i"


def _character_double(value):
    """R ``as.character`` for one double.

    Exact integers below 100000 keep their digits. Other values use fifteen
    significant digits, or sixteen when the magnitude is in ``[1e15, 1e16)``.
    The shorter of the fixed and scientific forms wins. ``-0`` prints as ``0``.
    """
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = math.copysign(1.0, value) < 0.0
    magnitude = abs(value)
    if magnitude < 1e5 and magnitude == math.trunc(magnitude):
        text = str(int(magnitude))
        return "-" + text if negative else text
    digits = 16 if 1e15 <= magnitude < 1e16 else 15
    with localcontext(_DECIMAL):
        rounded = _round_sig(Decimal(magnitude), digits)
        fixed, scientific = _fixed_and_sci(rounded)
        exponent = rounded.adjusted()
    if magnitude.is_integer():
        exact = str(int(magnitude))
        mantissa = scientific.split("e", 1)[0]
        if len(exact) < len(scientific) or (
            len(exact) == len(scientific) and "." in mantissa
        ):
            chosen = exact
        else:
            chosen = _choose_notation(fixed, scientific, exponent)
    else:
        chosen = _choose_notation(fixed, scientific, exponent)
    if negative:
        return "-" + chosen
    return chosen


def _round_sig(value, digits):
    if value == 0:
        return Decimal(0)
    adjusted = value.adjusted()
    quantum = Decimal("1e{}".format(adjusted - (digits - 1)))
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if rounded != 0 and rounded.adjusted() > adjusted:
        adjusted = rounded.adjusted()
        quantum = Decimal("1e{}".format(adjusted - (digits - 1)))
        rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return rounded


def _fixed_and_sci(rounded):
    if rounded == 0:
        return "0", "0e+00"
    text = format(rounded, "f")
    if "." in text:
        whole, frac = text.split(".")
        digits = (whole + frac).lstrip("0").rstrip("0") or "0"
    else:
        digits = text.lstrip("0").rstrip("0") or "0"
    adjusted = rounded.adjusted()
    if adjusted >= 0:
        if adjusted + 1 >= len(digits):
            fixed = digits + ("0" * (adjusted + 1 - len(digits)))
        else:
            fixed = digits[: adjusted + 1] + "." + digits[adjusted + 1 :]
    else:
        fixed = "0." + ("0" * (-adjusted - 1)) + digits
    mantissa = digits if len(digits) == 1 else digits[0] + "." + digits[1:]
    return fixed, f"{mantissa}e{adjusted:+03d}"


def _choose_notation(fixed, scientific, exponent):
    if len(scientific) < len(fixed):
        return scientific
    if len(scientific) > len(fixed):
        return fixed
    mantissa = scientific.split("e", 1)[0]
    if "." in mantissa:
        return fixed
    if exponent <= -4 or exponent >= 5:
        return scientific
    return fixed
