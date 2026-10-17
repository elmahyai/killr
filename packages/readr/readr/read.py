"""Delimited, fixed-width, and log readers."""

from __future__ import annotations

import bz2
import gzip
import io
import lzma
import sys
import warnings
import zipfile
from pathlib import Path

from tibble.frame import Tibble

from readr.columns import (
    ColSpec,
    Collector,
    as_col_spec,
    col_character,
    col_guess,
    col_skip,
    collector_for_name,
    cols,
)
from readr.locale import default_locale
from readr.names import repair_names
from readr.parse import guess_type, parse_one
from readr.runtime import edition_first, should_show_types
from readr.scan import guess_delim, log_records, parse_records, whitespace_records

_MISSING = object()


class Literal(str):
    """A string that is data, not a path. This is base R's I()."""


def I(text):
    """Mark a string as literal data so a newline does not warn."""
    return Literal(text)


class Table(Tibble):
    """A tibble plus the column spec and the parsing problems."""

    def __init__(self, names, columns, nrow, spec=None, problems=None):
        super().__init__(list(names), list(columns), nrow)
        self.spec = spec
        self.problems = list(problems or [])

    def __str__(self) -> str:
        header = " ".join(self.names)
        lines = [header] if header else ["<table>"]
        for row in range(self.nrow):
            cells = []
            for column in self.columns:
                value = column[row]
                cells.append("NA" if value is None else str(value))
            lines.append(" ".join(cells))
        return "\n".join(lines)


def _load_bytes(path: str) -> bytes:
    raw = Path(path).read_bytes()
    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    elif raw.startswith(b"BZh"):
        raw = bz2.decompress(raw)
    elif raw.startswith(b"\xfd7zXZ\x00"):
        raw = lzma.decompress(raw)
    elif raw.startswith(b"PK"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            name = archive.namelist()[0]
            raw = archive.read(name)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw


def _decode(raw: bytes, encoding: str) -> str:
    name = {"UTF-8": "utf-8", "latin1": "latin-1"}.get(encoding, encoding)
    return raw.decode(name, errors="replace")


def _source_text(file, encoding):
    """Return (text, label, multiple paths or None)."""
    if isinstance(file, (bytes, bytearray)):
        return _decode(bytes(file), encoding), "literal data", None
    if isinstance(file, Literal):
        return str(file), "literal data", None
    if isinstance(file, (list, tuple)):
        return None, None, list(file)
    if isinstance(file, Path):
        file = str(file)
    if isinstance(file, str):
        if "\n" in file and not Path(file).exists():
            if not isinstance(file, Literal):
                warnings.warn(
                    'file = "should use `I()` for literal data"',
                    stacklevel=3,
                )
            return file, "literal data", None
        if not Path(file).is_file():
            raise FileNotFoundError(file)
        return _decode(_load_bytes(file), encoding), file, None
    raise TypeError("Unknown input to `file`")


def _skip_text(text: str, skip: int) -> tuple[str, int]:
    if not skip:
        return text, 1
    index = 0
    seen = 0
    while seen < skip and index <= len(text):
        newline = text.find("\n", index)
        if newline < 0:
            return "", seen + 2
        index = newline + 1
        seen += 1
    return text[index:], seen + 1


def _sample(rows, guess_max):
    count = len(rows)
    if count == 0 or guess_max <= 0:
        return []
    guess_num = min(count, int(guess_max))
    step = count // guess_num if guess_num else 0
    chosen = [rows[index * step] for index in range(max(guess_num - 1, 0))]
    chosen.append(rows[-1])
    return chosen


def _align(fields, width, delim, edition):
    actual = len(fields)
    if actual == width:
        return fields, None
    if actual > width:
        if edition == 2 and width:
            head = list(fields[: width - 1])
            tail = fields[width - 1 :]
            joined = delim.join(text for text, _quoted in tail)
            head.append((joined, any(flag for _text, flag in tail)))
            return head, actual
        return list(fields[:width]), actual
    return list(fields) + [("", False)] * (width - actual), actual


def _names_for(header, col_names, width, name_repair):
    if col_names is True:
        names = [text for text, _quoted in header]
    elif col_names is False:
        names = [f"X{index}" for index in range(1, width + 1)]
    else:
        names = ["" if name is None else str(name) for name in col_names]
        if len(names) < width:
            names = names + [f"X{index}" for index in range(len(names) + 1, width + 1)]
        elif len(names) > width:
            names = names[:width]
    if len(names) < width:
        names = names + [f"X{index}" for index in range(len(names) + 1, width + 1)]
    return repair_names(names[:width], name_repair)


def _resolve_collectors(names, col_types, rows, guess_max, loc, na, trim_ws):
    spec = as_col_spec(col_types)
    named = [collector.fields.get("name") for collector in spec.cols]
    collectors = []
    if not spec.cols:
        collectors = [col_guess() for _ in names]
    elif all(name is None for name in named):
        collectors = list(spec.cols)
        if len(collectors) < len(names):
            collectors = collectors + [spec.default.copy() for _ in range(len(names) - len(collectors))]
        collectors = collectors[: len(names)]
    else:
        by_name = {
            collector.fields.get("name"): collector
            for collector in spec.cols
            if collector.fields.get("name")
        }
        for name in names:
            collectors.append(by_name.get(name, spec.default).copy())
    guessed_any = False
    if any(collector.kind == "guess" for collector in collectors) and rows:
        sampled = _sample(rows, guess_max if guess_max is not None else len(rows))
        for index, collector in enumerate(collectors):
            if collector.kind != "guess":
                continue
            column = []
            for row in sampled:
                if index >= len(row):
                    continue
                text, _quoted = row[index]
                if trim_ws:
                    text = text.strip(" \t")
                column.append(text)
            kind = guess_type(column, na, loc, False)
            collectors[index] = collector_for_name(kind)
            guessed_any = True
    for collector, name in zip(collectors, names):
        collector.fields["name"] = name
    kept = [(index, collector) for index, collector in enumerate(collectors) if collector.kind != "skip"]
    return kept, guessed_any, ColSpec([collector for _index, collector in kept], spec.default)


def _parse_columns(rows, kept, loc, na, trim_ws, quoted_na, label, edition):
    columns = []
    problems = []
    for index, collector in kept:
        values = []
        for line_no, row in rows:
            if index >= len(row):
                values.append(None)
                continue
            text, quoted = row[index]
            value, expected = parse_one(
                text, collector, loc, na, trim_ws, quoted, quoted_na
            )
            if expected is not None and edition == 1 and collector.kind == "date":
                pass
            values.append(value)
            if expected is not None:
                problems.append(
                    {
                        "row": line_no,
                        "col": index + 1,
                        "expected": expected,
                        "actual": text.strip(" \t") if trim_ws and text else text,
                        "file": label if edition == 1 or label != "literal data" else label,
                    }
                )
        columns.append(values)
    return columns, problems


def _show_spec(names, collectors, delim, nrow) -> None:
    groups: dict[str, list[str]] = {}
    order = []
    for name, collector in zip(names, collectors):
        kind = collector.kind
        if kind not in groups:
            groups[kind] = []
            order.append(kind)
        groups[kind].append(name)
    lines = [f"Rows: {nrow} Columns: {len(names)}", f'Delimiter: "{delim}"']
    for kind in order:
        shown = ", ".join(groups[kind][:20])
        lines.append(f"{kind} ({len(groups[kind])}): {shown}")
    print("\n".join(lines), file=sys.stderr)


def _warn_read(problems, edition) -> None:
    if not problems:
        return
    if edition == 2:
        warnings.warn(
            "One or more parsing issues, call `problems()` on your data frame for details,\n"
            "e.g.:\n"
            "  dat <- vroom(...)\n"
            "  problems(dat)",
            stacklevel=3,
        )
        return
    count = len(problems)
    noun = "parsing failure" if count == 1 else "parsing failures"
    warnings.warn(f"{count} {noun}.", stacklevel=3)


def read_delim(
    file,
    delim=None,
    quote='"',
    escape_backslash=False,
    escape_double=True,
    col_names=True,
    col_types=None,
    col_select=None,
    id=None,
    locale=None,
    na=("", "NA"),
    quoted_na=_MISSING,
    comment="",
    trim_ws=False,
    skip=0,
    n_max=float("inf"),
    guess_max=None,
    name_repair="unique",
    num_threads=None,
    progress=None,
    show_col_types=None,
    skip_empty_rows=True,
    lazy=None,
):
    """Read a delimited file. The default edition matches readr 2."""
    if delim is not None and delim == "":
        raise ValueError(
            "`delim` must be at least one character, use `read_table()` for whitespace delimited input."
        )
    if quoted_na is not _MISSING and not edition_first():
        raise ValueError(
            "quoted_na is not supported in readr edition 2. "
            "Use with_edition(1, ...) for the legacy parser."
        )
    loc = locale or default_locale()
    edition = 1 if edition_first() else 2
    use_quoted_na = True if quoted_na is _MISSING else bool(quoted_na)
    if guess_max is None:
        guess_max = n_max if n_max != float("inf") else 1000
    text, label, many = _source_text(file, loc.encoding)
    if many is not None:
        frames = [
            read_delim(
                path,
                delim=delim,
                quote=quote,
                escape_backslash=escape_backslash,
                escape_double=escape_double,
                col_names=col_names,
                col_types=col_types,
                col_select=col_select,
                id=None,
                locale=loc,
                na=na,
                quoted_na=_MISSING if quoted_na is _MISSING else quoted_na,
                comment=comment,
                trim_ws=trim_ws,
                skip=skip,
                n_max=n_max,
                guess_max=guess_max,
                name_repair=name_repair,
                show_col_types=False,
                skip_empty_rows=skip_empty_rows,
            )
            for path in many
        ]
        return _bind(frames, id, [str(path) for path in many])
    return _read_text(
        text,
        label,
        delim=delim,
        quote=quote,
        escape_backslash=escape_backslash,
        escape_double=escape_double,
        col_names=col_names,
        col_types=col_types,
        col_select=col_select,
        locale=loc,
        na=tuple(na),
        quoted_na=use_quoted_na,
        comment=comment or "",
        trim_ws=trim_ws,
        skip=int(skip or 0),
        n_max=n_max,
        guess_max=guess_max,
        name_repair=name_repair,
        show_col_types=show_col_types if show_col_types is not None else should_show_types(),
        skip_empty_rows=skip_empty_rows,
        edition=edition,
        whitespace=False,
        log=False,
    )


def _read_text(
    text,
    label,
    delim,
    quote,
    escape_backslash,
    escape_double,
    col_names,
    col_types,
    col_select,
    locale,
    na,
    quoted_na,
    comment,
    trim_ws,
    skip,
    n_max,
    guess_max,
    name_repair,
    show_col_types,
    skip_empty_rows,
    edition,
    whitespace=False,
    log=False,
    fwf=None,
):
    body, first_line = _skip_text(text, skip)
    if whitespace:
        records = whitespace_records(body, quote=quote or '"', comment=comment, skip_empty_rows=skip_empty_rows)
        delim = " "
    elif log:
        records = log_records(body)
        delim = " "
    elif fwf is not None:
        records = _fwf_records(body, fwf, skip_empty_rows, comment)
        delim = ""
    else:
        if delim is None:
            sample = []
            for line in body.splitlines():
                if comment and line.startswith(comment):
                    continue
                if skip_empty_rows and line == "":
                    continue
                sample.append(line)
                if len(sample) >= 20:
                    break
            delim = guess_delim(sample)
        records = parse_records(
            body,
            delim=delim,
            quote=quote or "",
            escape_backslash=escape_backslash,
            escape_double=escape_double,
            comment=comment,
            skip_empty_rows=skip_empty_rows,
        )
    records = [(line + first_line - 1, fields) for line, fields in records]
    if not records:
        table = Table([], [], 0, ColSpec([], col_guess()), [])
        return _select(table, col_select)
    if col_names is True:
        _header_line, header = records[0]
        data = records[1:]
        width = len(header)
    else:
        header = None
        data = records
        if isinstance(col_names, (list, tuple)) and edition == 1:
            width = len(col_names)
        else:
            width = len(data[0][1]) if data else (len(col_names) if isinstance(col_names, (list, tuple)) else 0)
    if isinstance(n_max, float) and n_max == float("inf"):
        limited = data
    else:
        limited = data[: int(n_max)]
    aligned = []
    count_problems = []
    for line_no, fields in data:
        fields, actual = _align(fields, width, delim, edition)
        aligned.append((line_no, fields))
        if actual is not None:
            count_problems.append(
                {
                    "row": line_no,
                    "col": None if edition == 1 else actual,
                    "expected": f"{width} columns",
                    "actual": f"{actual} columns",
                    "file": "literal data" if label == "literal data" and edition == 1 else label,
                }
            )
    aligned_limited = []
    allowed = {line for line, _fields in limited}
    # n_max limits data rows in order, not by line identity if duplicates
    aligned_limited = aligned[: len(limited)] if not (isinstance(n_max, float) and n_max == float("inf")) else aligned
    names = _names_for(header if header is not None else [("", False)] * width, col_names, width, name_repair)
    guess_rows = [fields for _line, fields in aligned]
    kept, guessed, spec = _resolve_collectors(
        names, col_types, guess_rows, 1000 if guess_max is None else guess_max, locale, na, trim_ws
    )
    out_names = [collector.fields.get("name") for _index, collector in kept]
    columns, problems = _parse_columns(
        aligned_limited, kept, locale, na, trim_ws, quoted_na, label if edition == 1 else label, edition
    )
    if edition == 2 and label == "literal data":
        for problem in problems:
            problem["file"] = label
    problems = count_problems + problems
    if isinstance(n_max, float) and n_max == float("inf"):
        pass
    else:
        # column-count problems on rows past n_max stay out
        keep_lines = {line for line, _fields in aligned_limited}
        problems = [problem for problem in problems if problem["row"] in keep_lines or problem in count_problems and problem["row"] in keep_lines]
        problems = [
            problem
            for problem in (count_problems + problems)
        ]
    # rebuild cleanly
    visible_lines = {line for line, _fields in aligned_limited}
    problems = [
        problem
        for problem in (count_problems + problems)
        if problem["row"] in visible_lines
    ]
    # the double-add above is messy; recompute from the two lists
    problems = [problem for problem in count_problems if problem["row"] in visible_lines]
    _columns, parse_problems = _parse_columns(
        aligned_limited, kept, locale, na, trim_ws, quoted_na, label, edition
    )
    columns = _columns
    problems.extend(parse_problems)
    nrow = len(aligned_limited)
    if show_col_types is None:
        show_col_types = should_show_types()
    supplied = col_types is not None
    if show_col_types is True or (show_col_types is None and guessed and not supplied):
        _show_spec(out_names, [collector for _index, collector in kept], delim, nrow)
    _warn_read(problems, edition)
    table = Table(out_names, columns, nrow, spec, problems)
    return _select(table, col_select)


def _select(table: Table, col_select):
    if not col_select:
        return table
    chosen = []
    names = []
    for item in col_select:
        if isinstance(item, int):
            index = item
            chosen.append(table.columns[index])
            names.append(table.names[index])
        else:
            index = table.names.index(item)
            chosen.append(table.columns[index])
            names.append(table.names[index])
    return Table(names, chosen, table.nrow, table.spec, table.problems)


def _bind(frames, id_name, labels):
    if not frames:
        return Table([], [], 0)
    if id_name:
        names = [id_name] + list(frames[0].names)
    else:
        names = list(frames[0].names)
    columns = [[] for _ in names]
    for frame, label in zip(frames, labels):
        offset = 1 if id_name else 0
        if id_name:
            columns[0].extend([label] * frame.nrow)
        for index, column in enumerate(frame.columns):
            columns[offset + index].extend(list(column))
    problems = []
    for frame in frames:
        problems.extend(frame.problems)
    return Table(names, columns, sum(frame.nrow for frame in frames), frames[0].spec, problems)


def read_csv(file, col_names=True, col_types=None, col_select=None, id=None, locale=None, na=("", "NA"), quoted_na=_MISSING, quote='"', comment="", trim_ws=True, skip=0, n_max=float("inf"), guess_max=None, name_repair="unique", num_threads=None, progress=None, show_col_types=None, skip_empty_rows=True, lazy=None):
    return read_delim(
        file, delim=",", quote=quote, escape_backslash=False, escape_double=True,
        col_names=col_names, col_types=col_types, col_select=col_select, id=id,
        locale=locale, na=na, quoted_na=quoted_na, comment=comment, trim_ws=trim_ws,
        skip=skip, n_max=n_max, guess_max=guess_max, name_repair=name_repair,
        num_threads=num_threads, progress=progress, show_col_types=show_col_types,
        skip_empty_rows=skip_empty_rows, lazy=lazy,
    )


def read_csv2(file, col_names=True, col_types=None, col_select=None, id=None, locale=None, na=("", "NA"), quoted_na=_MISSING, quote='"', comment="", trim_ws=True, skip=0, n_max=float("inf"), guess_max=None, progress=None, name_repair="unique", num_threads=None, show_col_types=None, skip_empty_rows=True, lazy=None):
    loc = locale or default_locale()
    if loc.decimal_mark == ".":
        print(
            'Using "," as decimal and "." as grouping mark. Use read_delim() for more control.',
            file=sys.stderr,
        )
        from readr.locale import locale as make_locale

        loc = make_locale(
            loc.date_names,
            loc.date_format,
            loc.time_format,
            decimal_mark=",",
            grouping_mark=".",
            tz=loc.tz,
            encoding=loc.encoding,
        )
    return read_delim(
        file, delim=";", quote=quote, col_names=col_names, col_types=col_types,
        col_select=col_select, id=id, locale=loc, na=na, quoted_na=quoted_na,
        comment=comment, trim_ws=trim_ws, skip=skip, n_max=n_max, guess_max=guess_max,
        name_repair=name_repair, num_threads=num_threads, progress=progress,
        show_col_types=show_col_types, skip_empty_rows=skip_empty_rows, lazy=lazy,
    )


def read_tsv(file, col_names=True, col_types=None, col_select=None, id=None, locale=None, na=("", "NA"), quoted_na=_MISSING, quote='"', comment="", trim_ws=True, skip=0, n_max=float("inf"), guess_max=None, progress=None, name_repair="unique", num_threads=None, show_col_types=None, skip_empty_rows=True, lazy=None):
    return read_delim(
        file, delim="\t", quote=quote, col_names=col_names, col_types=col_types,
        col_select=col_select, id=id, locale=locale, na=na, quoted_na=quoted_na,
        comment=comment, trim_ws=trim_ws, skip=skip, n_max=n_max, guess_max=guess_max,
        progress=progress, name_repair=name_repair, num_threads=num_threads,
        show_col_types=show_col_types, skip_empty_rows=skip_empty_rows, lazy=lazy,
    )


def read_table(file, col_names=True, col_types=None, locale=None, na=("", "NA"), skip=0, n_max=float("inf"), guess_max=None, progress=None, comment="", show_col_types=None, skip_empty_rows=True, name_repair="unique"):
    loc = locale or default_locale()
    text, label, many = _source_text(file, loc.encoding)
    if many is not None:
        raise ValueError("read_table() reads one file")
    return _read_text(
        text, label, delim=" ", quote='"', escape_backslash=False, escape_double=True,
        col_names=col_names, col_types=col_types, col_select=None, locale=loc,
        na=tuple(na), quoted_na=True, comment=comment or "", trim_ws=True, skip=int(skip or 0),
        n_max=n_max, guess_max=guess_max if guess_max is not None else 1000,
        name_repair=name_repair, show_col_types=show_col_types if show_col_types is not None else should_show_types(),
        skip_empty_rows=skip_empty_rows, edition=1 if edition_first() else 2, whitespace=True,
    )


def read_log(file, col_names=False, col_types=None, trim_ws=True, skip=0, n_max=float("inf"), show_col_types=None, progress=None):
    loc = default_locale()
    text, label, _many = _source_text(file, loc.encoding)
    return _read_text(
        text, label, delim=" ", quote='"', escape_backslash=False, escape_double=True,
        col_names=col_names, col_types=col_types, col_select=None, locale=loc,
        na=("-", "", "NA"), quoted_na=True, comment="", trim_ws=trim_ws, skip=int(skip or 0),
        n_max=n_max, guess_max=1000, name_repair="minimal",
        show_col_types=show_col_types if show_col_types is not None else should_show_types(),
        skip_empty_rows=True, edition=1 if edition_first() else 2, log=True,
    )


def _fwf_records(text, positions, skip_empty_rows, comment):
    records = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if comment and line.startswith(comment):
            continue
        if skip_empty_rows and line.strip(" \t") == "":
            continue
        fields = []
        for begin, end in positions:
            if end is None:
                piece = line[begin:]
            else:
                piece = line[begin:end]
            fields.append((piece, False))
        records.append((line_no, fields))
    return records


def read_fwf(file, col_positions=None, col_types=None, locale=None, na=("", "NA"), comment="", trim_ws=True, skip=0, n_max=float("inf"), guess_max=None, progress=None, name_repair="unique", num_threads=None, show_col_types=None, skip_empty_rows=True, lazy=None):
    loc = locale or default_locale()
    text, label, _many = _source_text(file, loc.encoding)
    if col_positions is None:
        col_positions = fwf_empty(file, skip=skip, comment=comment)
    positions = list(zip(col_positions["begin"], col_positions["end"]))
    names = list(col_positions["col_names"])
    table = _read_text(
        text, label, delim="", quote="", escape_backslash=False, escape_double=True,
        col_names=names, col_types=col_types, col_select=None, locale=loc, na=tuple(na),
        quoted_na=True, comment=comment or "", trim_ws=trim_ws, skip=int(skip or 0),
        n_max=n_max, guess_max=guess_max if guess_max is not None else 1000,
        name_repair=name_repair,
        show_col_types=show_col_types if show_col_types is not None else should_show_types(),
        skip_empty_rows=skip_empty_rows, edition=1 if edition_first() else 2,
        fwf=positions,
    )
    return table


def fwf_widths(widths, col_names=None):
    """Column widths. The last width may be None when the field runs to the end of the line."""
    begin = []
    end = []
    cursor = 0
    for width in widths:
        begin.append(cursor)
        if width is None:
            end.append(None)
            cursor += 1
        else:
            cursor += int(width)
            end.append(cursor)
    return _fwf_spec(begin, end, col_names)


def fwf_positions(start, end=None, col_names=None):
    """1-based inclusive positions. `end` may be None for a ragged last field."""
    if end is None:
        raise ValueError("end positions are required")
    begin = [int(value) - 1 for value in start]
    exclusive = [None if value is None else int(value) for value in end]
    return _fwf_spec(begin, exclusive, col_names)


def fwf_cols(**columns):
    """Named widths, or named (start, end) pairs. Positions are 1-based."""
    if not columns:
        return _fwf_spec([], [], [])
    first = next(iter(columns.values()))
    if isinstance(first, (list, tuple)):
        start = [int(value[0]) for value in columns.values()]
        end = [None if value[1] is None else int(value[1]) for value in columns.values()]
        return fwf_positions(start, end, list(columns))
    return fwf_widths(list(columns.values()), list(columns))


def fwf_empty(file, skip=0, col_names=None, comment="", n=100):
    """Guess column positions from runs of two or more spaces."""
    from readr.locale import default_locale as locale_now

    text, _label, _many = _source_text(file, locale_now().encoding)
    body, _line = _skip_text(text, int(skip or 0))
    lines = []
    for line in body.splitlines():
        if comment and line.startswith(comment):
            continue
        if line.strip() == "":
            continue
        lines.append(line)
        if len(lines) >= int(n):
            break
    if not lines:
        return _fwf_spec([], [], col_names)
    width = max(len(line) for line in lines)
    padded = [line.ljust(width) for line in lines]
    gap = [all(line[index] == " " for line in padded) for index in range(width)]
    begin = []
    end = []
    index = 0
    while index < width:
        while index < width and gap[index]:
            index += 1
        if index >= width:
            break
        start = index
        while index < width and not gap[index]:
            index += 1
        begin.append(start)
        end.append(index)
    if end:
        end[-1] = None
    return _fwf_spec(begin, end, col_names, ragged=True)


def _fwf_spec(begin, end, col_names, ragged=False):
    count = len(begin)
    if col_names is None:
        names = [f"X{index}" for index in range(1, count + 1)]
    else:
        names = ["" if name is None else str(name) for name in col_names]
        for index, name in enumerate(names):
            if name == "" and index < count:
                names[index] = f"X{index + 1}"
    return {"begin": begin, "end": end, "col_names": names}


def spec(x):
    """The column specification stored on a data frame from `read_*`."""
    return getattr(x, "spec", None)


def problems(x=None):
    """Parsing problems: row, column, expected, actual, and file."""
    found = [] if x is None else list(getattr(x, "problems", []) or [])
    rows = [problem["row"] for problem in found]
    cols = [problem["col"] for problem in found]
    expected = [problem["expected"] for problem in found]
    actual = [problem["actual"] for problem in found]
    files = [problem.get("file", "") for problem in found]
    return Table(
        ["row", "col", "expected", "actual", "file"],
        [rows, cols, expected, actual, files],
        len(found),
    )


def stop_for_problems(x):
    """Raise if `x` has any parsing problems."""
    found = list(getattr(x, "problems", []) or [])
    if not found:
        return x
    count = len(found)
    noun = "parsing failure" if count == 1 else "parsing failures"
    raise ValueError(f"{count} {noun}")


def count_fields(file, tokenizer, skip=0, n_max=-1):
    """How many fields are on each record."""
    loc = default_locale()
    text, _label, _many = _source_text(file, loc.encoding)
    body, _line = _skip_text(text, int(skip or 0))
    records = _records_from_tokenizer(body, tokenizer)
    counts = [len(fields) for _line, fields in records]
    if n_max is not None and int(n_max) >= 0:
        counts = counts[: int(n_max)]
    return counts


def tokenize(file, tokenizer=None, skip=0, n_max=-1):
    """Records as lists of strings."""
    from readr.columns import col_character as _unused  # noqa: F401

    loc = default_locale()
    text, _label, _many = _source_text(file, loc.encoding)
    body, _line = _skip_text(text, int(skip or 0))
    if tokenizer is None:
        tokenizer = {"delim": ",", "quote": '"', "comment": "", "trim_ws": True, "skip_empty_rows": True, "escape_double": True, "escape_backslash": False, "kind": "delim"}
    records = _records_from_tokenizer(body, tokenizer)
    if n_max is not None and int(n_max) >= 0:
        records = records[: int(n_max)]
    rows = []
    trim = tokenizer.get("trim_ws", False) if isinstance(tokenizer, dict) else False
    for _line, fields in records:
        values = []
        for text_value, _quoted in fields:
            if trim:
                text_value = text_value.strip(" \t")
            values.append(text_value)
        rows.append(values)
    return rows


def _records_from_tokenizer(text, tokenizer):
    if not isinstance(tokenizer, dict):
        tokenizer = vars(tokenizer) if hasattr(tokenizer, "__dict__") else {}
    kind = tokenizer.get("kind") or tokenizer.get("class") or "delim"
    if kind in ("fwf", "tokenizer_fwf"):
        positions = list(zip(tokenizer.get("begin", []), tokenizer.get("end", [])))
        return _fwf_records(text, positions, tokenizer.get("skip_empty_rows", True), tokenizer.get("comment", ""))
    if kind in ("ws", "tokenizer_ws"):
        return whitespace_records(text, comment=tokenizer.get("comment", ""), skip_empty_rows=tokenizer.get("skip_empty_rows", True))
    if kind in ("log", "tokenizer_log"):
        return log_records(text)
    return parse_records(
        text,
        delim=tokenizer.get("delim", ","),
        quote=tokenizer.get("quote", '"'),
        escape_backslash=tokenizer.get("escape_backslash", False),
        escape_double=tokenizer.get("escape_double", True),
        comment=tokenizer.get("comment", ""),
        skip_empty_rows=tokenizer.get("skip_empty_rows", True),
    )


def tokenizer_delim(delim, quote='"', na="NA", quoted_na=True, comment="", trim_ws=True, escape_double=True, escape_backslash=False, skip_empty_rows=True):
    return {"kind": "delim", "delim": delim, "quote": quote, "na": na, "quoted_na": quoted_na, "comment": comment, "trim_ws": trim_ws, "escape_double": escape_double, "escape_backslash": escape_backslash, "skip_empty_rows": skip_empty_rows}


def tokenizer_csv(na="NA", quoted_na=True, quote='"', comment="", trim_ws=True, skip_empty_rows=True):
    return tokenizer_delim(",", quote, na, quoted_na, comment, trim_ws, True, False, skip_empty_rows)


def tokenizer_tsv(na="NA", quoted_na=True, quote='"', comment="", trim_ws=True, skip_empty_rows=True):
    return tokenizer_delim("\t", quote, na, quoted_na, comment, trim_ws, True, False, skip_empty_rows)


def tokenizer_fwf(begin, end, na="NA", comment="", trim_ws=True, skip_empty_rows=True):
    return {"kind": "fwf", "begin": list(begin), "end": list(end), "na": na, "comment": comment, "trim_ws": trim_ws, "skip_empty_rows": skip_empty_rows}


def tokenizer_line(na=(), skip_empty_rows=True):
    return {"kind": "line", "na": na, "skip_empty_rows": skip_empty_rows, "delim": "\n", "quote": "", "comment": "", "trim_ws": False, "escape_double": False, "escape_backslash": False}


def tokenizer_log(trim_ws):
    return {"kind": "log", "trim_ws": trim_ws}


def tokenizer_ws(na="NA", comment="", skip_empty_rows=True):
    return {"kind": "ws", "na": na, "comment": comment, "skip_empty_rows": skip_empty_rows}


def spec_delim(file, delim=None, **kwargs):
    frame = read_delim(file, delim=delim, n_max=0, guess_max=kwargs.pop("guess_max", 1000), show_col_types=False, **kwargs)
    return frame.spec


def spec_csv(file, **kwargs):
    frame = read_csv(file, n_max=0, guess_max=kwargs.pop("guess_max", 1000), show_col_types=False, **kwargs)
    return frame.spec


def spec_csv2(file, **kwargs):
    frame = read_csv2(file, n_max=0, guess_max=kwargs.pop("guess_max", 1000), show_col_types=False, **kwargs)
    return frame.spec


def spec_tsv(file, **kwargs):
    frame = read_tsv(file, n_max=0, guess_max=kwargs.pop("guess_max", 1000), show_col_types=False, **kwargs)
    return frame.spec


def spec_table(file, **kwargs):
    frame = read_table(file, n_max=0, guess_max=kwargs.pop("guess_max", 1000), show_col_types=False, **kwargs)
    return frame.spec


def type_convert(df, col_types=None, na=("", "NA"), trim_ws=True, locale=None, guess_integer=False):
    """Re-parse character columns."""
    loc = locale or default_locale()
    if not isinstance(df, Tibble) and not hasattr(df, "names"):
        raise TypeError("type_convert() expects a data frame")
    names = list(df.names)
    columns = []
    character = []
    for name, column in zip(names, df.columns):
        if column and all(value is None or isinstance(value, str) for value in column):
            character.append(name)
        columns.append(list(column))
    if not character:
        warnings.warn(
            "`type_convert()` only converts columns of type 'character'.\n- `df` has no columns of type 'character'",
            stacklevel=2,
        )
        return df
    spec = as_col_spec(col_types)
    by_name = {}
    if spec.cols and any(collector.fields.get("name") for collector in spec.cols):
        by_name = {collector.fields["name"]: collector for collector in spec.cols if collector.fields.get("name")}
    out_spec_cols = []
    for index, name in enumerate(names):
        if name not in character:
            continue
        if name in by_name:
            collector = by_name[name]
        elif spec.cols and not by_name:
            position = character.index(name)
            collector = spec.cols[position] if position < len(spec.cols) else spec.default
        else:
            kind = guess_type(columns[index], tuple(na), loc, guess_integer)
            collector = collector_for_name(kind)
        parsed = []
        for value in columns[index]:
            result, _expected = parse_one(
                "" if value is None else value,
                collector,
                loc,
                tuple(na),
                trim_ws,
            )
            parsed.append(result)
        columns[index] = parsed
        collector = collector.copy()
        collector.fields["name"] = name
        out_spec_cols.append(collector)
    return Table(names, columns, df.nrow, ColSpec(out_spec_cols, spec.default), getattr(df, "problems", []))
