"""Python translation of the R package tools."""

from tools.checkmd5 import check_md5sums
from tools.conditions import assert_condition, assert_error, assert_warning
from tools.concordance import as_rconcordance, follow_concordance, match_concordance
from tools.data import adobe_glyphs, charset_to_unicode
from tools.checksum import md5sum, sha256sum
from tools.convert import to_html, to_rd
from tools.defunct import get_dep_list, install_found_depends, package_dependencies, pkg_depends, vignette_depends
from tools.deps import depends_on_pkgs, package_dependencies as package_dependency_graph
from tools.delim import delim_match
from tools.file_ext import NA_character_, file_ext
from tools.htmlheader import html_header
from tools.latex import deparse_latex, encoded_text_to_latex, latex_to_utf8
from tools.index import read_00index
from tools.options import get_bibstyle, print_via_format, rd2txt_options
from tools.nons3 import non_s3_methods
from tools.paths import (
    file_path_as_absolute,
    file_path_sans_ext,
    list_files_with_exts,
    list_files_with_type,
)
from tools.rda import check_rda_files
from tools.rcmd import rcmd
from tools.rdiff import rdiff
from tools.process import (
    SIGCHLD,
    SIGCONT,
    SIGHUP,
    SIGINT,
    SIGKILL,
    SIGQUIT,
    SIGSTOP,
    SIGTERM,
    SIGTSTP,
    SIGUSR1,
    SIGUSR2,
    pskill,
    psnice,
)
from tools.sweave import sweave_tex_filter
from tools.session import (
    R_user_dir,
    find_gs_cmd,
    lang_elts,
    makevars_site,
    makevars_user,
    standard_package_names,
)
from tools.vignette import vignette_engine, vignette_info
from tools.textutil import (
    parse_uri_reference,
    show_non_ascii,
    show_non_ascii_file,
    to_title_case,
)

__all__ = [
    "NA_character_",
    "adobe_glyphs",
    "as_rconcordance",
    "assert_condition",
    "assert_error",
    "assert_warning",
    "check_rda_files",
    "charset_to_unicode",
    "R_user_dir",
    "check_md5sums",
    "delim_match",
    "depends_on_pkgs",
    "deparse_latex",
    "encoded_text_to_latex",
    "follow_concordance",
    "get_bibstyle",
    "get_dep_list",
    "html_header",
    "install_found_depends",
    "match_concordance",
    "pkg_depends",
    "print_via_format",
    "rd2txt_options",
    "rcmd",
    "rdiff",
    "read_00index",
    "vignette_depends",
    "vignette_engine",
    "vignette_info",
    "SIGCHLD",
    "SIGCONT",
    "SIGHUP",
    "SIGINT",
    "SIGKILL",
    "SIGQUIT",
    "SIGSTOP",
    "SIGTERM",
    "SIGTSTP",
    "SIGUSR1",
    "SIGUSR2",
    "file_ext",
    "file_path_as_absolute",
    "file_path_sans_ext",
    "find_gs_cmd",
    "lang_elts",
    "latex_to_utf8",
    "list_files_with_exts",
    "list_files_with_type",
    "makevars_site",
    "makevars_user",
    "md5sum",
    "non_s3_methods",
    "package_dependencies",
    "package_dependency_graph",
    "parse_uri_reference",
    "pskill",
    "psnice",
    "sha256sum",
    "show_non_ascii",
    "show_non_ascii_file",
    "standard_package_names",
    "sweave_tex_filter",
    "to_html",
    "to_rd",
    "to_title_case",
    "check_tnf",
]
from tools.license import analyze_license
from tools.bibstyle import bibstyle
from tools.base_aliases_db import base_aliases_db
from tools.check_tnf import check_tnf
