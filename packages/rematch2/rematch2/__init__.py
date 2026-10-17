"""Python translation of the R package rematch2."""

from rematch2.bind_re_match import bind_re_match, bind_re_match_
from rematch2.re_exec import re_exec
from rematch2.re_exec_all import re_exec_all
from rematch2.re_match import re_match
from rematch2.re_match_all import re_match_all
from rematch2.records import dollar_rematch_allrecords, dollar_rematch_records

__all__ = [
    "bind_re_match",
    "bind_re_match_",
    "dollar_rematch_allrecords",
    "dollar_rematch_records",
    "re_exec",
    "re_exec_all",
    "re_match",
    "re_match_all",
]
