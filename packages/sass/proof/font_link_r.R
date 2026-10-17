# R reference for sass::font_link() (sass 0.4.10).
# The stylesheet is only linked in the page head, so nothing is fetched here.
here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])))
source(file.path(here, "_sass_r_common.R"))

cases <- list(
  plain = function() canon_collection(font_link("Open Sans", "https://fonts.example.com/css2?family=Open+Sans&display=swap")),
  escaped = function() canon_collection(font_link("Lato", "https://example.com/a b.css?x='1'&y=2")),
  bad_family = function() canon_collection(font_link(c("A", "B"), "https://example.com/x.css"))
)

timed <- function() font_link("Open Sans", "https://fonts.example.com/css2?family=Open+Sans&display=swap")

run_proof("font_link", cases, timed, "plain",
          file.path(here, "outputs", "font_link_r.json"))
