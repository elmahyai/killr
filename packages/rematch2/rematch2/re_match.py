"""re_match: the first match and its capture groups, one row per string."""

from rematch2._engine import (
    as_text,
    compile_pattern,
    first_match,
    match_string,
)
from tibble import new_tibble


def re_match(text, pattern, perl=True, ignore_case=False, fixed=False):
    strings = as_text(text)
    compiled, names = compile_pattern(
        pattern, perl=perl, ignore_case=ignore_case, fixed=fixed
    )
    found = [first_match(value, compiled) for value in strings]
    columns = []
    column_names = []
    for index, name in enumerate(names, start=1):
        columns.append(
            [match_string(value, match, index) for value, match in zip(strings, found)]
        )
        column_names.append(name)
    columns.append(list(strings))
    column_names.append(".text")
    columns.append(
        [match_string(value, match, 0) for value, match in zip(strings, found)]
    )
    column_names.append(".match")
    return new_tibble(columns, names=column_names, nrow=len(strings))
