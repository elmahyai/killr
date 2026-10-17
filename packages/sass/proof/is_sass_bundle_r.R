# R reference for sass::is_sass_bundle() (sass 0.4.10).
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

bundle_obj <- sass_bundle(a = "x")

cases <- list(
  bundle = function() is_sass_bundle(bundle_obj),
  bundle_rules_arg = function() is_sass_bundle(sass_bundle(rules = "x")),
  layer_struct = function() is_sass_bundle(sass:::sass_layer_struct(rules = "x")),
  string = function() is_sass_bundle("x"),
  null = function() is_sass_bundle(NULL),
  plain_list = function() is_sass_bundle(list(layers = list())),
  font_collection = function() is_sass_bundle(font_collection("Roboto"))
)

timed <- function() is_sass_bundle(bundle_obj)

run_proof("is_sass_bundle", cases, timed, "bundle",
          file.path(here, "outputs", "is_sass_bundle_r.json"))
