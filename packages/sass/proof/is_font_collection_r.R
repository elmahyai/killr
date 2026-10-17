# R reference for sass::is_font_collection() (sass 0.4.10).
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

fc_obj <- font_collection("Roboto")

cases <- list(
  font_collection = function() is_font_collection(fc_obj),
  font_face = function() is_font_collection(font_face("Open Sans", src = "url(a.woff2)")),
  string = function() is_font_collection("Roboto"),
  null = function() is_font_collection(NULL),
  bundle = function() is_font_collection(sass_bundle(a = "x")),
  plain_list = function() is_font_collection(list(families = "x"))
)

timed <- function() is_font_collection(fc_obj)

run_proof("is_font_collection", cases, timed, "font_collection",
          file.path(here, "outputs", "is_font_collection_r.json"))
