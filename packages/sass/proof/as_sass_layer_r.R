# R reference for sass::as_sass_layer() (sass 0.4.10).
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

bundle_input <- sass_bundle(a = list(x = 1), b = "p{q:r}")

cases <- list(
  layer_input = function() canon_layer(as_sass_layer(sass:::sass_layer_struct(rules = "a{b:c}"))),
  character = function() canon_layer(as_sass_layer("a{b:c}")),
  numeric = function() canon_layer(as_sass_layer(1)),
  named_list = function() canon_layer(as_sass_layer(list(x = 1))),
  unnamed_list = function() canon_layer(as_sass_layer(list("a{}", "b{}"))),
  bundle_two_defaults = function() canon_layer(as_sass_layer(sass_bundle(a = list(x = 1), b = list(x = 2)))),
  bundle_mixed = function() canon_layer(as_sass_layer(bundle_input)),
  null = function() canon_layer(as_sass_layer(NULL))
)

timed <- function() as_sass_layer(bundle_input)

run_proof("as_sass_layer", cases, timed, "bundle_mixed",
          file.path(here, "outputs", "as_sass_layer_r.json"))
