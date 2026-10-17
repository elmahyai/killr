"""Bit fields and name tables from fansi src/fansi-cnst.h and R/constants.R."""

VALID_TERM_CAP = ("all", "bright", "256", "truecolor", "old")
VALID_CTL = ("all", "nl", "c0", "sgr", "csi", "esc", "url", "osc")
VALID_ROUND = ("start", "stop", "both", "neither")
VALID_TYPES = ("chars", "width", "graphemes", "bytes")

CTL_NL = 1
CTL_C0 = 2
CTL_SGR = 4
CTL_CSI = 8
CTL_ESC = 16
CTL_URL = 32
CTL_OSC = 64
CTL_ALL = 127

TERM_BRIGHT = 1
TERM_256 = 2
TERM_TRUECOLOR = 4
TERM_ALL = 7

SET_CTL = 0
SET_TERMCAP = 7
SET_WARN = 10
SET_WIDTH = 21

WARN_MASK = 2096128
WARN_ALL = 2047
WARN_MANGLED = 163840
WARN_UTF8 = 524288
WARN_ERROR = 1572864

COUNT_CHARS = 0
COUNT_WIDTH = 1
COUNT_GRAPH = 2
COUNT_BYTES = 3

SET_ALLOWNA = 8388608
SET_KEEPNA = 16777216
SET_ESCONE = 33554432
SET_TERMOLD = 67108864

STAT_ERR_START = 7
STAT_ERR_ALL = 15
STAT_ZWJ = 2048
STAT_RI = 4096
STAT_AGAIN = 8192
STAT_WARNED = 16384
STAT_SPECIAL = 32768
STAT_OVERSHOT = 65536
STAT_DONE = 131072
STAT_PERSIST = 22528

ERR_UNKNOWN_SUB = 1
ERR_BAD_SUB = 2
ERR_EXCEED_CAP = 3
ERR_NOT_SPECIAL = 4
ERR_NOT_SPECIAL_BAD_SUB = 5
ERR_BAD_CSI_OSC = 6
ERR_ESC_OTHER = 7
ERR_ESC_OTHER_BAD = 8
ERR_C0 = 9
ERR_BAD_UTF8 = 10
ERR_NON_ASCII = 11

STL_BOLD = 1
STL_BLUR = 2
STL_ITALIC = 4
STL_UNDER = 8
STL_BLINK1 = 16
STL_BLINK2 = 32
STL_INVERT = 64
STL_CONCEAL = 128
STL_CROSSOUT = 256
STL_FRAKTUR = 512
STL_UNDER2 = 1024
STL_PROPSPC = 2048
STL_MASK = 4095
STL_MASK1 = 511
STL_MASK2 = 447

BRD_FRAMED = 4096
BRD_ENCIRC = 8192
BRD_OVERLN = 16384
BRD_MASK = 28672

IDG_UNDERL = 32768
IDG_UNDERL2 = 65536
IDG_OVERL = 131072
IDG_OVERL2 = 262144
IDG_STRESS = 524288
IDG_MASK = 1015808

FONT_START = 20
FONT_ALL = 31

CLR_OFF = 0
CLR_8 = 16
CLR_BRIGHT = 32
CLR_256 = 64
CLR_TRU = 128

RND_START = 1
RND_STOP = 2
RND_BOTH = 3
RND_NEITHER = 4

ERR_MESSAGES = (
    "a CSI SGR sequence with unknown substrings or a OSC hyperlink with unsupported parameters",
    "a CSI SGR sequence or OSC hyperlink with invalid substrings",
    "a CSI SGR sequence with color codes not supported by terminal",
    "a non-SGR CSI or a non-URL OSC sequence",
    "a non-SGR CSI or a non-URL OSC sequence with invalid substrings",
    "a malformed CSI or OSC sequence",
    "a non-CSI/OSC escape sequence",
    "a malformed escape sequence",
    "a C0 control character",
    "a malformed UTF-8 sequence",
    "an illegal non-ASCII byte",
)


def get_range(value, offset, bits):
    return (value >> offset) & bits


def set_range(value, offset, bits, val):
    return (value & ~((bits) << offset)) | ((val & bits) << offset)


def ctl_as_int(indexes):
    """Compress 1-based match() indexes the way FANSI_ctl_as_int does."""
    ctl_int = 0
    flip = False
    for index in indexes:
        ctl_val = index - 2
        if ctl_val > 6:
            raise RuntimeError("Internal Error: max ctl value allowed is 6.")
        if ctl_val < 0:
            flip = True
        else:
            ctl_int |= 1 << ctl_val
    if flip:
        ctl_int ^= CTL_ALL
    return ctl_int


def term_cap_as_int(indexes):
    """Compress 1-based match() indexes the way FANSI_term_cap_as_int does."""
    term = 0
    flip = False
    for index in indexes:
        term_val = index - 2
        if term_val > 3:
            raise RuntimeError("Internal Error: max term_cap value allowed is 2.")
        if term_val < 0:
            flip = True
        else:
            term |= 1 << term_val
    if flip:
        term ^= TERM_ALL
    return term
