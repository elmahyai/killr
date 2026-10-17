"""re_exec_all: every match, with start and end positions."""

from rematch2._engine import all_matches, all_record, as_text, compile_pattern
from rematch2.records import RematchAllRecords
from tibble import new_tibble


def _column(strings, found, group):
    rows = [all_record(value, matches, group) for value, matches in zip(strings, found)]
    return RematchAllRecords(rows)


def re_exec_all(text, pattern, perl=True, ignore_case=False, fixed=False):
    strings = as_text(text)
    compiled, names = compile_pattern(
        pattern, perl=perl, ignore_case=ignore_case, fixed=fixed
    )
    if len(strings) == 0:
        columns = [RematchAllRecords([]) for _ in names]
        columns.append([])
        columns.append(RematchAllRecords([]))
        return new_tibble(columns, names=[*names, ".text", ".match"], nrow=0)
    found = [all_matches(value, compiled) for value in strings]
    columns = [_column(strings, found, index) for index in range(1, len(names) + 1)]
    columns.append(list(strings))
    columns.append(_column(strings, found, 0))
    return new_tibble(
        columns, names=[*names, ".text", ".match"], nrow=len(strings)
    )
