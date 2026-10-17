# R reference for sass::sass() (sass 0.4.10).
# cache = FALSE on every call, so each call compiles. R's default cache would
# return stored CSS and the timing would measure a cache read.
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

out_file <- file.path(here, "outputs", "sass_output.css")

cases <- list(
  string = function() as.character(sass("a{b:c}", cache = FALSE)),
  named_defaults = function() as.character(sass(list(x = "1px", "a{b:$x}"), cache = FALSE)),
  compressed = function() as.character(sass("a{b:c}", options = sass_options(output_style = "compressed"), cache = FALSE)),
  nested_indent4 = function() as.character(sass(".a { b: c; .d { e: f } }",
    options = sass_options(output_style = "nested", indent_width = 4), cache = FALSE)),
  compact = function() as.character(sass(".a { b: c; .d { e: f } }",
    options = sass_options(output_style = "compact"), cache = FALSE)),
  nested_tab = function() as.character(sass(".a { b: c; .d { e: f } }",
    options = sass_options(output_style = "nested", indent_type = "tab"), cache = FALSE)),
  precision2 = function() as.character(sass("a{b: 1px / 3}", options = sass_options(precision = 2), cache = FALSE)),
  indented_syntax = function() as.character(sass("a\n  b: c", options = sass_options(indented_syntax = TRUE), cache = FALSE)),
  output_file = function() {
    r <- sass("a{b:c}", output = out_file, cache = FALSE)
    list(returned = basename(as.character(r)), file = read_bytes_text(out_file))
  },
  null_input = function() as.character(sass(NULL, cache = FALSE)),
  bad_style = function() as.character(sass("a{b:c}", options = sass_options(output_style = "x"), cache = FALSE))
)

timed <- function() sass(list(x = "1px", "a{b:$x}"), cache = FALSE)

run_proof("sass", cases, timed, "named_defaults",
          file.path(here, "outputs", "sass_r.json"))
