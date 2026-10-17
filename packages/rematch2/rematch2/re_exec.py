"""re_exec: the first match, with start and end positions."""

from rematch2._engine import as_text, compile_pattern, first_match, match_record
from rematch2.records import RematchRecords
from tibble import new_tibble


def _column(strings, found, group):
    rows = [
        match_record(value, match, group) for value, match in zip(strings, found)
    ]
    return RematchRecords(rows)


def re_exec(text, pattern, perl=True, ignore_case=False, fixed=False):
    strings = as_text(text)
    compiled, names = compile_pattern(
        pattern, perl=perl, ignore_case=ignore_case, fixed=fixed
    )
    found = [first_match(value, compiled) for value in strings]
    columns = [_column(strings, found, index) for index in range(1, len(names) + 1)]
    columns.append(list(strings))
    columns.append(_column(strings, found, 0))
    return new_tibble(
        columns, names=[*names, ".text", ".match"], nrow=len(strings)
    )
