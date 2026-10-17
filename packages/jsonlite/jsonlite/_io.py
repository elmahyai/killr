"""Read, write, and stream JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonlite._decode import fromJSON, parse_json
from jsonlite._encode import toJSON
from jsonlite._frames import rbind_pages
from jsonlite._values import DataFrame


def read_json(path: str, *, simplify_vector: bool = False, **options: Any) -> Any:
    """Read a file. Vectors stay lists unless ``simplify_vector`` is true."""

    text = Path(path).read_text(encoding="utf-8")
    return parse_json(text, simplify_vector=simplify_vector, **options)


def write_json(x: Any, path: str, **options: Any) -> None:
    """Write JSON and a trailing newline, the way writeLines does."""

    Path(path).write_text(toJSON(x, **options) + "\n", encoding="utf-8")


def stream_out(x: DataFrame, con: Any = None, *, verbose: bool = False) -> None:
    """Write one minified JSON object per row."""

    if not isinstance(x, DataFrame):
        raise TypeError("stream_out currently supports data frames")
    from jsonlite._encode import _encode

    rows = _encode(
        x,
        dataframe="rows",
        digits=4,
        signif=False,
        auto_unbox=False,
        null="list",
        na="omit",
        factor="string",
        collapse=False,
    )
    text = "\n".join(rows) + ("\n" if rows else "")
    if con is None:
        print(text, end="")
        return text
    if hasattr(con, "write"):
        con.write(text)
        return None
    Path(con).write_text(text, encoding="utf-8")
    return None


def stream_in(con: Any, *, verbose: bool = False) -> DataFrame:
    """Read newline-delimited JSON objects and bind them into one data frame."""

    if hasattr(con, "read"):
        raw = con.read()
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    else:
        text = Path(con).read_text(encoding="utf-8")
    records = []
    for line in text.splitlines():
        if line.strip():
            records.append(fromJSON(line, simplify_vector=False))
    if not records:
        return DataFrame({})
    return rbind_pages([_one_row(record) for record in records])


def _one_row(record: dict) -> DataFrame:
    return DataFrame({key: [value] for key, value in record.items()})
