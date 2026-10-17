# R reference for sass::font_google() (sass 0.4.10).
# The default local = TRUE path is run. R reads the Google stylesheet and the
# font file from the offline fixture cache (fixtures/google_local), so the
# proof makes no network call. cache is the fixture cache, which is the only
# change from the default; the default cache is a disk directory that is empty
# here, and would download.
# cache = NULL is passed for the local = FALSE cases so no disk cache is used.
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))
source(file.path(here, "_sass_dep_common.R"))

fixture_cache <- google_fixture_cache()

cases <- list(
  plain_link = function() canon_collection(font_google("Roboto", local = FALSE, cache = NULL)),
  axes_wght_ital = function() canon_collection(font_google("Roboto", local = FALSE, cache = NULL,
                                                           wght = c(700, 400), ital = c(1, 0))),
  wght_only_block = function() canon_collection(font_google("Open Sans", local = FALSE, cache = NULL,
                                                            wght = c(300, 400), display = "block")),
  ital_only = function() canon_collection(font_google("Lato", local = FALSE, cache = NULL, ital = 1)),
  local_default = function() canon_collection(font_google("Roboto", cache = fixture_cache)),
  bad_local = function() canon_collection(font_google("Roboto", local = "yes", cache = NULL)),
  bad_ital = function() canon_collection(font_google("Roboto", local = FALSE, cache = NULL, ital = 2))
)

timed <- function() font_google("Roboto", cache = fixture_cache)$html_deps()

run_proof("font_google", cases, timed, "local_default",
          file.path(here, "outputs", "font_google_r.json"))
