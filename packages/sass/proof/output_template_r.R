# R reference for sass::output_template() (sass 0.4.10).
# Cases with a suffix give fixed paths. Without one, R picks a random name,
# so that case checks the shape of the path instead.
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

tpl <- file.path(here, "outputs", "output_template")

cases <- list(
  suffix_css = function() output_template(basename = "out", dirname = "dir", path = tpl)(suffix = "-s"),
  suffix_min_css = function() output_template(basename = "out", dirname = "dir", path = tpl)(
    options = list(output_style = 3), suffix = "-m"),
  expanded_css = function() output_template(basename = "out", dirname = "dir", path = tpl)(
    options = list(output_style = 1), suffix = "-e"),
  fileext_given = function() output_template(basename = "out", dirname = "dir", fileext = ".txt", path = tpl)(
    options = list(output_style = 2), suffix = "-t"),
  default_dirname = function() output_template(basename = "page", path = tpl)(suffix = "-d"),
  no_suffix_shape = function() {
    r <- output_template(basename = "out", dirname = "dir", path = tpl)()
    res <- list(
      parent_is_template = dirname(dirname(r)) == tpl,
      dir_has_prefix = startsWith(basename(dirname(r)), "dir"),
      file_name = basename(r)
    )
    unlink(dirname(r), recursive = TRUE)
    res
  }
)

timed <- function() output_template(basename = "out", dirname = "dir", path = tpl)(suffix = "-s")

run_proof("output_template", cases, timed, "suffix_css",
          file.path(here, "outputs", "output_template_r.json"))
