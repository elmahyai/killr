# R reference for sass::font_collection() (sass 0.4.10).
# Fonts are compared with each html dependency rendered. The local = TRUE
# font is built from the offline fixture cache, so no network is used.
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))
source(file.path(here, "_sass_dep_common.R"))

fixture_cache <- google_fixture_cache()

cases <- list(
  plain = function() canon_collection(font_collection("Roboto")),
  two_families_quoted = function() canon_collection(font_collection("Open Sans", "serif", default_flag = FALSE)),
  quote_false = function() canon_collection(font_collection("Open Sans", "serif", quote = FALSE)),
  face = function() canon_collection(font_collection(face = list(family = "Open Sans", src = "url(a.woff2)", weight = 400))),
  link = function() canon_collection(font_collection(link = list(family = "Lato", href = "https://example.com/lato.css"))),
  google_link = function() canon_collection(font_collection(google = list(family = "Roboto", local = FALSE, cache = NULL, wght = c(400, 700)))),
  google_local_default = function() canon_collection(font_collection(google = list(family = "Roboto", local = TRUE, cache = fixture_cache))),
  collection_nested = function() canon_collection(font_collection(collection = list("Roboto", "serif"))),
  mixed_order_link = function() canon_collection(font_collection(
    "Open Sans", google = list(family = "Roboto", local = FALSE, cache = NULL), "serif"
  )),
  mixed_order_local = function() canon_collection(font_collection(
    "Open Sans", google = list(family = "Roboto", local = TRUE, cache = fixture_cache), "serif", default_flag = FALSE
  )),
  unsupported_name = function() canon_collection(font_collection(bogus = list("x"))),
  non_string = function() canon_collection(font_collection(1))
)

timed <- function() font_collection("Open Sans", "serif", default_flag = FALSE)

run_proof("font_collection", cases, timed, "two_families_quoted",
          file.path(here, "outputs", "font_collection_r.json"))
