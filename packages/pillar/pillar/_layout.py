"""Widths, ticks, and the small helpers the table printers share.

``match.arg(NULL)`` is the first choice, so a missing alignment stays left
inside ``align``. A deprecation line is wrapped after the ``Error:`` prefix
is added and then that prefix is removed, which is how lifecycle's message
breaks at the session width.
"""

from __future__ import annotations

import math
import re
from typing import Any

from cli.symbol import symbol

from pillar._options import get_option
from pillar._text import is_na, paste_atom
from pillar._width import display_extent
from pillar.extent import align, get_extent, get_max_extent

NBSP = "\u00a0"
_INT_MIN = -2147483647
_INT_MAX = 2147483647


def option(name: str, default: Any) -> Any:
    value = get_option(name)
    if value is None and name not in ("pillar.width",):
        # An unset pillar.width means "use the session width".
        if name == "width":
            return default
        stored = get_option(name, default)
        return default if stored is None else stored
    if value is None:
        return default
    return value


def session_width() -> int:
    chosen = get_option("pillar.width")
    if chosen is None:
        chosen = get_option("width", 80)
    if chosen is None:
        return 80
    if isinstance(chosen, float) and math.isinf(chosen):
        return 10**9
    return int(chosen)


def width_print(width: Any) -> int:
    if width is not None:
        return int(width)
    return session_width()


def big_mark(value: Any) -> str:
    """formatC digits. A missing count is ``??``."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "??"
    mark = "." if get_option("OutDec") == "," else ","
    number = int(value)
    sign = "-" if number < 0 else ""
    digits = str(abs(number))
    parts: list[str] = []
    while digits:
        parts.append(digits[-3:])
        digits = digits[:-3]
    return sign + mark.join(reversed(parts))


def seq2(start: int, end: int) -> list[int]:
    """rlang::seq2. A backward pair is empty, unlike ``start:end``."""

    if start > end:
        return []
    return list(range(start, end + 1))


def pluralise_n(message: str, n: int) -> str:
    if n < 0:
        raise ValueError("n >= 0 is not TRUE")
    if n == 1:
        message = re.sub(r"\[([^\] ]* *)\]", r"\1", message)
        message = re.sub(r"\([^\) ]* *\)", "", message)
    else:
        message = re.sub(r"\(([^\) ]* *)\)", r"\1", message)
        message = re.sub(r"\[[^\] ]* *\]", "", message)
    return message


def ellipsis() -> str:
    return symbol["continue"]


def strwrap(text: str, width: int) -> list[str]:
    """Base ``strwrap`` for one paragraph. The width counts characters."""

    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def defunct_message(when: str, what: str, with_: str | None = None) -> str:
    """The text ``lifecycle::deprecate_stop`` shows for a pillar function.

    The first line is prefixed with ``Error:`` before it is wrapped at the
    session width, and that prefix is then removed. A replacement is an
    info bullet on the next line.
    """

    package, _, fn = what.partition("::")
    if not fn:
        package, fn = "pillar", what
    if fn.endswith("()"):
        bare = fn[:-2]
    else:
        bare = fn
    label = f"`{bare}()`"
    line = f"{label} was deprecated in {package} {when} and is now defunct."
    width = session_width()
    wrapped = strwrap("Error: " + line, width)
    if wrapped:
        wrapped[0] = re.sub(r"^Error: ?", "", wrapped[0])
    if with_:
        wpkg, _, wfn = with_.partition("::")
        if wfn.endswith("()"):
            wfn = wfn[:-2]
        shown = f"{wpkg}::{wfn}" if wpkg and wpkg != package else wfn
        wrapped.append(f"{symbol['info']} Please use `{shown}()` instead.")
    return "\n".join(wrapped)


def is_syntactic(name: str) -> bool:
    if is_na(name) or name == "":
        return False
    if not re.fullmatch(r"[A-Za-z.][A-Za-z0-9._]*", name):
        return False
    if re.fullmatch(r"\.[0-9].*", name):
        return False
    if name in {"if", "else", "repeat", "while", "function", "for", "in", "next", "break", "TRUE", "FALSE", "NULL", "Inf", "NaN", "NA", "NA_integer_", "NA_real_", "NA_complex_", "NA_character_"}:
        return False
    return True


def tick(name: Any) -> str:
    if is_na(name):
        return "NA"
    text = str(name).replace("\\", "\\\\").replace("`", "\\`")
    return "`" + text + "`"


def tick_if_needed(names: Any) -> Any:
    if names is None:
        return None
    scalar = isinstance(names, str) or is_na(names)
    items = [names] if scalar else list(names)
    out = [item if isinstance(item, str) and is_syntactic(item) else tick(item) for item in items]
    if scalar:
        return out[0]
    return out


def prepare_title(title: Any) -> Any:
    if title is None:
        return None
    if isinstance(title, str) or is_na(title):
        parts = [title]
    else:
        parts = list(title)
    if not parts:
        return title
    last = "" if parts[-1] is None else str(parts[-1])
    if last.startswith("["):
        head = "$".join("" if part is None else str(part) for part in parts[:-1])
        return head + last
    return "$".join("" if part is None else str(part) for part in parts)


def trunc_back(text: str, width: int) -> str:
    from cli.ansi_text import ansi_substr

    if display_extent(text) <= width:
        return text
    kept = ansi_substr(text, 1, max(width - 1, 0))
    return kept + ellipsis()


def str_trunc(values: list[Any], width: Any, shorten: str | None = None) -> list[Any]:
    if isinstance(width, float) and math.isinf(width):
        return list(values)
    mode = shorten or "back"
    out: list[Any] = []
    for item in values:
        if is_na(item) or display_extent(item) <= width:
            out.append(item)
            continue
        if mode == "back":
            out.append(trunc_back(paste_atom(item), int(width)))
        else:
            out.append(trunc_back(paste_atom(item), int(width)))
    return out


def distribute_pillars(widths: list[int], tier_widths: list[int]) -> dict[str, list[Any]]:
    """Place column widths into tiers. A column that does not fit is NA."""

    tier: list[Any] = [None] * len(widths)
    offset: list[Any] = [None] * len(widths)
    current_tier = 1
    current_x = 0
    for index, current_width in enumerate(widths):
        if not tier_widths or current_tier > len(tier_widths):
            break
        if current_x + current_width > tier_widths[current_tier - 1]:
            if current_width > tier_widths[current_tier - 1]:
                if current_tier == len(tier_widths) or current_width > tier_widths[current_tier]:
                    break
            current_tier += 1
            current_x = 0
            if current_tier > len(tier_widths):
                break
        tier[index] = current_tier
        current_x += current_width
        offset[index] = current_x
        current_x += 1
    return {
        "id": list(range(1, len(widths) + 1)),
        "tier": tier,
        "width": list(widths),
        "offset_after": offset,
    }


def distribute_pillars_rev(widths: list[int], tier_widths: list[int]) -> dict[str, list[Any]]:
    """Place widths from the right, the way ``distribute_pillars_rev`` does."""

    rev = distribute_pillars(list(reversed(widths)), list(reversed(tier_widths)))
    count = len(widths)
    tier = list(reversed(rev["tier"]))
    width_col = list(reversed(rev["width"]))
    n_tiers = len(tier_widths)
    new_tier: list[Any] = []
    for item in tier:
        if item is None:
            new_tier.append(None)
        else:
            new_tier.append(n_tiers + 1 - item)
    seen: list[int] = []
    for item in new_tier:
        if item is not None and item not in seen:
            seen.append(item)
    groups: dict[int, list[int]] = {item: [] for item in seen}
    for index, item in enumerate(new_tier):
        if item is not None:
            groups[item].append(index)
    new_offset: list[Any] = [None] * count
    for item in seen:
        indexes = groups[item]
        running = 0
        totals: list[int] = []
        for index in indexes:
            running += int(width_col[index]) + 1
            totals.append(running)
        peak = max(totals) if totals else 0
        budget = tier_widths[item - 1]
        for index, total in zip(indexes, totals):
            new_offset[index] = total - peak + budget
    return {
        "id": list(range(1, count + 1)),
        "tier": new_tier,
        "width": width_col,
        "offset_after": new_offset,
    }


def get_tier_widths(width: int, ncol: int, rowid_width: int, tier_width: int | None = None) -> list[int]:
    if tier_width is None:
        tier_width = int(get_option("width", 80) or 80)
    if isinstance(width, float) and not math.isfinite(width):
        pos = [index * tier_width for index in range(ncol + 1)]
    elif width < tier_width:
        pos = [0, int(width)]
    else:
        pos = list(range(0, int(width) + tier_width, tier_width))
        # seq(0, width + tier_width - 1, by = tier_width)
        limit = int(width) + tier_width - 1
        pos = []
        cursor = 0
        while cursor <= limit:
            pos.append(cursor)
            cursor += tier_width
    widths = [pos[index + 1] - pos[index] - rowid_width for index in range(len(pos) - 1)]
    return [item for item in widths if item >= 1]


def as_r_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    number = int(math.trunc(float(value)))
    if number < _INT_MIN or number > _INT_MAX:
        return None
    return number


def lines_of(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if hasattr(value, "x") and hasattr(value, "align"):
        return [paste_atom(item) for item in value.x]
    return [paste_atom(item) for item in value]


def extent_of(value: Any) -> int:
    if value is None or value == "":
        return 0
    return int(display_extent(value))


def align_lines(lines: list[str], width: int, side: str) -> list[str]:
    if not lines:
        return []
    aligned = align(lines, width=width, align=side)
    if isinstance(aligned, str):
        return [aligned]
    return list(aligned)


def max_extent(lines: list[str]) -> int:
    if not lines:
        return 0
    return get_max_extent(lines)
