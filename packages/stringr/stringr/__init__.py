"""Python translation of the R package stringr.

Exports are filled in after each translated function is checked.
"""

from stringr.case import (
    str_to_camel,
    str_to_kebab,
    str_to_lower,
    str_to_sentence,
    str_to_snake,
    str_to_title,
    str_to_upper,
)
from stringr.count import str_count
from stringr.data import fruit, sentences, words
from stringr.detect import str_detect, str_ends, str_ilike, str_like, str_starts, str_which
from stringr.dup import str_dup
from stringr.equal import str_equal
from stringr.escape import str_conv, str_escape
from stringr.extract import str_extract, str_extract_all
from stringr.glue import str_glue, str_glue_data
from stringr.interp import str_interp
from stringr.join import str_c, str_flatten, str_flatten_comma
from stringr.length import str_length, str_width
from stringr.locate import invert_match, str_locate, str_locate_all
from stringr.match import str_match, str_match_all
from stringr.pad import str_pad
from stringr.pattern import boundary, coll, fixed, regex
from stringr.replace import str_remove, str_remove_all, str_replace, str_replace_all, str_replace_na
from stringr.pipe import pipe
from stringr.sort import str_order, str_rank, str_sort
from stringr.split import str_split, str_split_1, str_split_fixed, str_split_i
from stringr.sub import str_sub, str_sub_all, str_sub_assign
from stringr.subset import str_subset
from stringr.trim import str_squish, str_trim
from stringr.trunc import str_trunc
from stringr.unique import str_unique
from stringr.view import str_view, str_view_all
from stringr.word import word
from stringr.wrap import str_wrap

__all__ = [
    "boundary",
    "coll",
    "fixed",
    "fruit",
    "invert_match",
    "pipe",
    "regex",
    "sentences",
    "str_c",
    "str_conv",
    "str_count",
    "str_detect",
    "str_dup",
    "str_ends",
    "str_equal",
    "str_escape",
    "str_extract",
    "str_extract_all",
    "str_flatten",
    "str_flatten_comma",
    "str_glue",
    "str_glue_data",
    "str_ilike",
    "str_interp",
    "str_length",
    "str_like",
    "str_locate",
    "str_locate_all",
    "str_match",
    "str_match_all",
    "str_order",
    "str_pad",
    "str_rank",
    "str_remove",
    "str_remove_all",
    "str_replace",
    "str_replace_all",
    "str_replace_na",
    "str_sort",
    "str_split",
    "str_split_1",
    "str_split_fixed",
    "str_split_i",
    "str_squish",
    "str_starts",
    "str_sub",
    "str_sub_all",
    "str_sub_assign",
    "str_subset",
    "str_to_camel",
    "str_to_kebab",
    "str_to_lower",
    "str_to_sentence",
    "str_to_snake",
    "str_to_title",
    "str_to_upper",
    "str_trim",
    "str_trunc",
    "str_unique",
    "str_view",
    "str_view_all",
    "str_which",
    "str_width",
    "str_wrap",
    "word",
    "words",
]
