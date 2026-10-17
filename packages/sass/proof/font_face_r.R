# R reference for sass::font_face() (sass 0.4.10).
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

cases <- list(
  basic = function() canon_collection(font_face("Open Sans", src = "url(a.woff2)", weight = 400, style = "normal")),
  vectors = function() canon_collection(font_face(
    c("Roboto", "Helvetica Neue"), src = c("url(a.woff2)", "url(b.woff)"),
    unicode_range = c("U+0000-00FF", "U+0131"), display = "block",
    stretch = "condensed", variant = "small-caps")),
  no_display = function() canon_collection(font_face("Foo", src = "url(f.woff2)", display = NULL)),
  partial_display = function() canon_collection(font_face("Foo", src = "url(f.woff2)", display = "sw")),
  bad_display = function() canon_collection(font_face("Foo", src = "url(f.woff2)", display = "nope"))
)

timed <- function() font_face(
  c("Roboto", "Helvetica Neue"), src = c("url(a.woff2)", "url(b.woff)"),
  unicode_range = c("U+0000-00FF", "U+0131"), display = "block",
  stretch = "condensed", variant = "small-caps")

run_proof("font_face", cases, timed, "vectors",
          file.path(here, "outputs", "font_face_r.json"))
