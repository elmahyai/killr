"""Python translation of readr 2.2.0.

Edition 2 is the default. Values are read eagerly; `lazy=True` does not
defer parsing. Chunk callbacks are ordinary callables. Time of day is a
small value that prints like hms. Time zones use zoneinfo.
"""

from readr.callback import (
    AccumulateCallback,
    ChunkCallback,
    DataFrameCallback,
    ListCallback,
    SideEffectChunkCallback,
    read_csv2_chunked,
    read_csv_chunked,
    read_delim_chunked,
    read_tsv_chunked,
)
from readr.columns import (
    as_col_spec,
    col_character,
    col_date,
    col_datetime,
    col_double,
    col_factor,
    col_guess,
    col_integer,
    col_logical,
    col_number,
    col_skip,
    col_time,
    cols,
    cols_condense,
    cols_only,
)
from readr.lines import (
    read_file,
    read_file_raw,
    read_lines,
    read_lines_chunked,
    read_lines_raw,
    read_lines_raw_chunked,
)
from readr.locale import (
    date_names,
    date_names_lang,
    date_names_langs,
    default_locale,
    locale,
)
from readr.parse import (
    guess_parser,
    parse_character,
    parse_date,
    parse_datetime,
    parse_double,
    parse_factor,
    parse_guess,
    parse_integer,
    parse_logical,
    parse_number,
    parse_time,
    parse_vector,
)
from readr.read import (
    I,
    count_fields,
    fwf_cols,
    fwf_empty,
    fwf_positions,
    fwf_widths,
    problems,
    read_csv,
    read_csv2,
    read_delim,
    read_fwf,
    read_log,
    read_table,
    read_tsv,
    spec,
    spec_csv,
    spec_csv2,
    spec_delim,
    spec_table,
    spec_tsv,
    stop_for_problems,
    tokenize,
    tokenizer_csv,
    tokenizer_delim,
    tokenizer_fwf,
    tokenizer_line,
    tokenizer_log,
    tokenizer_tsv,
    tokenizer_ws,
    type_convert,
)
from readr.rds import read_rds, write_rds
from readr.runtime import (
    edition_get,
    local_edition,
    readr_example,
    readr_threads,
    should_read_lazy,
    should_show_types,
    show_progress,
    with_edition,
)
from readr.write import (
    format_csv,
    format_csv2,
    format_delim,
    format_tsv,
    output_column,
    write_csv,
    write_csv2,
    write_delim,
    write_excel_csv,
    write_excel_csv2,
    write_file,
    write_lines,
    write_tsv,
)

__all__ = [
    "AccumulateCallback",
    "ChunkCallback",
    "DataFrameCallback",
    "I",
    "ListCallback",
    "SideEffectChunkCallback",
    "as_col_spec",
    "clipboard",
    "col_character",
    "col_date",
    "col_datetime",
    "col_double",
    "col_factor",
    "col_guess",
    "col_integer",
    "col_logical",
    "col_number",
    "col_skip",
    "col_time",
    "cols",
    "cols_condense",
    "cols_only",
    "count_fields",
    "datasource",
    "date_names",
    "date_names_lang",
    "date_names_langs",
    "default_locale",
    "edition_get",
    "format_csv",
    "format_csv2",
    "format_delim",
    "format_tsv",
    "fwf_cols",
    "fwf_empty",
    "fwf_positions",
    "fwf_widths",
    "guess_encoding",
    "guess_parser",
    "local_edition",
    "locale",
    "output_column",
    "parse_character",
    "parse_date",
    "parse_datetime",
    "parse_double",
    "parse_factor",
    "parse_guess",
    "parse_integer",
    "parse_logical",
    "parse_number",
    "parse_time",
    "parse_vector",
    "problems",
    "read_csv",
    "read_csv2",
    "read_csv2_chunked",
    "read_csv_chunked",
    "read_delim",
    "read_delim_chunked",
    "read_file",
    "read_file_raw",
    "read_fwf",
    "read_lines",
    "read_lines_chunked",
    "read_lines_raw",
    "read_lines_raw_chunked",
    "read_builtin",
    "read_log",
    "read_rds",
    "read_table",
    "read_tsv",
    "read_tsv_chunked",
    "readr_example",
    "readr_threads",
    "should_read_lazy",
    "should_show_types",
    "show_progress",
    "spec",
    "spec_csv",
    "spec_csv2",
    "spec_delim",
    "spec_table",
    "spec_tsv",
    "stop_for_problems",
    "tokenize",
    "tokenizer_csv",
    "tokenizer_delim",
    "tokenizer_fwf",
    "tokenizer_line",
    "tokenizer_log",
    "tokenizer_tsv",
    "tokenizer_ws",
    "type_convert",
    "with_edition",
    "write_csv",
    "write_csv2",
    "write_delim",
    "write_excel_csv",
    "write_excel_csv2",
    "write_file",
    "write_lines",
    "write_rds",
    "write_tsv",
]


def read_builtin(x, package=None):
    """Read one dataset from a package, forcing the lazy-load promise.

    A warning from the lookup, including a missing name, is raised.
    """
    if not isinstance(x, str):
        raise ValueError("x must be a string")
    if package is not None and not isinstance(package, str):
        raise ValueError("package must be a string")
    import warnings

    from utils.data import data

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        loaded = data(list=x, package=package)
    if x not in loaded:
        raise ValueError(f"data set '{x}' not found")
    return loaded[x]


def clipboard():
    """Literal data from the clipboard, one line joined with newlines.

    Edition 1 returns the character vector from clipr. Edition 2 returns
    that vector pasted into one string, the same shape ``I()`` gives.
    """
    from clipr.read_clip import read_clip
    from readr.runtime import edition_first

    lines = read_clip()
    if lines is None:
        lines = []
    if isinstance(lines, str):
        text = lines
        lines = text.split("\n")
    else:
        text = "\n".join("" if line is None else str(line) for line in lines)
    if edition_first():
        return lines
    return I(text)


def datasource(file, skip=0, skip_empty_rows=False, comment="", skip_quote=True):
    """Where a reader will take its text from."""
    return {
        "file": file,
        "skip": skip,
        "skip_empty_rows": skip_empty_rows,
        "comment": comment,
        "skip_quote": skip_quote,
    }


def guess_encoding(file, n_max=10000, threshold=0.20):
    """Encodings stringi would report above `threshold`."""
    from readr.lines import read_file_raw, read_lines_raw
    from readr.read import Table

    try:
        from stringi.encoding import stri_enc_detect, stri_enc_isascii
    except ImportError as exc:
        raise RuntimeError("stringi package required for encoding operations") from exc
    if isinstance(file, (bytes, bytearray)):
        raw = bytes(file)
    elif isinstance(file, list) and file and isinstance(file[0], int):
        raw = bytes(file)
    elif isinstance(file, list) and file and isinstance(file[0], (bytes, bytearray)):
        raw = b"".join(bytes(line) for line in file)
    elif isinstance(file, list) and file and isinstance(file[0], list):
        raw = bytes(byte for line in file for byte in line)
    else:
        lines = read_lines_raw(file, n_max=n_max)
        raw = bytes(byte for line in lines for byte in line)
    if not raw or stri_enc_isascii(raw) is True:
        return Table(["encoding", "confidence"], [["ASCII"], [1.0]], 1)
    detected = stri_enc_detect(raw)
    if isinstance(detected, list):
        detected = detected[0]
    encodings = list(detected["Encoding"])
    confidences = list(detected["Confidence"])
    kept_e = []
    kept_c = []
    for encoding, confidence in zip(encodings, confidences):
        if confidence is None or confidence > threshold:
            kept_e.append(encoding)
            kept_c.append(confidence)
    return Table(["encoding", "confidence"], [kept_e, kept_c], len(kept_e))
