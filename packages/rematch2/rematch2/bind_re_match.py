"""Attach re_match columns to a tibble.

R's bind_re_match takes an unquoted column name. `from` is a Python keyword,
so both functions take that name as `column`, a string.
"""

from rematch2.re_match import re_match
from tibble import has_name, new_tibble, repair_names


def bind_re_match_(df, column, pattern, keep_match=False, **options):
    if not has_name(df, column):
        raise ValueError(f"{column} is not present in the data frame.")
    matched = re_match(df[column], pattern, **options)
    keep = []
    names = []
    for name, values in zip(matched.names, matched.columns):
        if name == ".text":
            continue
        if name == ".match" and not keep_match:
            continue
        names.append(name)
        keep.append(values)
    joined_names = list(df.names) + names
    joined_columns = list(df.columns) + keep
    return repair_names(new_tibble(joined_columns, names=joined_names, nrow=df.nrow))


def bind_re_match(df, column, pattern, keep_match=False, **options):
    return bind_re_match_(
        df, column, pattern, keep_match=keep_match, **options
    )
