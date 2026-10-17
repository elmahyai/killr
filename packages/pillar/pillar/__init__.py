"""Python translation of the R package pillar.

Column formatting for tables. The calls pillar makes are implemented here.
Defunct exports stop through lifecycle. ggplot2 scales are left out.
"""

from pillar.char import char, set_char_opts
from pillar.colonnade import colonnade, extra_cols, squeeze
from pillar.column import (
    ctl_new_pillar,
    ctl_new_pillar_list,
    ctl_new_rowid_pillar,
    new_pillar,
    pillar,
)
from pillar.deprecated import expect_known_display, is_vector_s3
from pillar.format_tbl import (
    tbl_format_body,
    tbl_format_footer,
    tbl_format_header,
    tbl_format_setup,
    tbl_nrow,
)
from pillar.glimpse import format_glimpse, glimpse
from pillar.shaft import new_pillar_shaft, new_pillar_shaft_simple, pillar_shaft
from pillar.extent import align, get_extent, get_max_extent, new_ornament
from pillar.num import num, set_num_opts
from pillar.parts import (
    new_pillar_component,
    new_pillar_title,
    new_pillar_type,
    pillar_component,
)
from pillar.styles import (
    AsIs,
    format_type_sum,
    style_bold,
    style_na,
    style_neg,
    style_num,
    style_subtle,
    style_subtle_num,
)
from pillar.summary import dim_desc, obj_sum, size_sum, tbl_sum, type_sum

__all__ = [
    "AsIs",
    "align",
    "char",
    "colonnade",
    "ctl_new_pillar",
    "ctl_new_pillar_list",
    "ctl_new_rowid_pillar",
    "expect_known_display",
    "extra_cols",
    "format_glimpse",
    "glimpse",
    "is_vector_s3",
    "new_pillar",
    "new_pillar_shaft",
    "new_pillar_shaft_simple",
    "pillar",
    "pillar_shaft",
    "squeeze",
    "tbl_format_body",
    "tbl_format_footer",
    "tbl_format_header",
    "tbl_format_setup",
    "tbl_nrow",
    "dim_desc",
    "format_type_sum",
    "get_extent",
    "get_max_extent",
    "new_ornament",
    "new_pillar_component",
    "new_pillar_title",
    "new_pillar_type",
    "num",
    "obj_sum",
    "pillar_component",
    "set_char_opts",
    "set_num_opts",
    "size_sum",
    "style_bold",
    "style_na",
    "style_neg",
    "style_num",
    "style_subtle",
    "style_subtle_num",
    "tbl_sum",
    "type_sum",
]
