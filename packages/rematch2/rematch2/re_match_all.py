"""re_match_all: every match, as list columns."""

from rematch2._engine import all_matches, all_strings, as_text, compile_pattern
from tibble import new_tibble


def re_match_all(text, pattern, perl=True, ignore_case=False, fixed=False):
    strings = as_text(text)
    compiled, names = compile_pattern(
        pattern, perl=perl, ignore_case=ignore_case, fixed=fixed
    )
    if len(strings) == 0:
        columns = [[] for _ in names]
        columns.append([])
        columns.append([])
        return new_tibble(
            columns, names=[*names, ".text", ".match"], nrow=0
        )
    found = [all_matches(value, compiled) for value in strings]
    columns = []
    for index, _name in enumerate(names, start=1):
        columns.append(
            [all_strings(value, matches, index) for value, matches in zip(strings, found)]
        )
    columns.append(list(strings))
    columns.append(
        [all_strings(value, matches, 0) for value, matches in zip(strings, found)]
    )
    return new_tibble(columns, names=[*names, ".text", ".match"], nrow=len(strings))
