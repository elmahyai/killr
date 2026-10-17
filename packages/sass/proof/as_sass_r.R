# R reference for sass::as_sass() (sass 0.4.10).
# Each case returns the text and the html dependencies (the html_dependencies
# attribute), so the dependency list is compared too.
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))
source(file.path(here, "_sass_dep_common.R"))

bundle_input <- sass_bundle(a = list(x = 1), b = "p{q:r}")
fixture_cache <- google_fixture_cache()

cases <- list(
  string = function() as_html_case(as_sass("a{b:c}")),
  character_vector = function() as_html_case(as_sass(c(".a{", "  b: c", "}"))),
  null = function() as_html_case(as_sass(NULL)),
  numeric = function() as_html_case(as_sass(3.5)),
  integer_valued = function() as_html_case(as_sass(12)),
  logical = function() as_html_case(as_sass(TRUE)),
  named_list = function() as_html_case(as_sass(list(x = 1, y = "red"))),
  layer = function() as_html_case(as_sass(sass:::sass_layer_struct(defaults = list(x = 1), rules = "a{b:c}"))),
  bundle = function() as_html_case(as_sass(bundle_input)),
  font_collection = function() as_html_case(as_sass(font_collection("Open Sans"))),
  google_local_default = function() as_html_case(as_sass(list(
    list("font-variable" = font_google("Roboto", cache = fixture_cache)),
    "body{font-family: $font-variable}"
  ))),
  google_link = function() as_html_case(as_sass(font_google("Roboto", local = FALSE, cache = NULL))),
  bundle_font = function() as_html_case(as_sass(sass_bundle(
    a = list("font-variable" = font_google("Roboto", cache = fixture_cache))
  ))),
  layer_html_dep = function() as_html_case(as_sass(sass_layer(
    html_deps = htmltools::htmlDependency("zz", "1.0", src = proof_fixture("dep_src"),
                                          stylesheet = "zz.css"),
    rules = "a{b:c}"
  ))),
  unsupported_class = function() as_html_case(as_sass(structure(list(), class = "zzz")))
)

timed <- function() as_sass(bundle_input)

run_proof("as_sass", cases, timed, "bundle",
          file.path(here, "outputs", "as_sass_r.json"))
