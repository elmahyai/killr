.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.color.pretty_color
colors <- list(
  "red", "#FF0000", "navy", "gray50", "grey50", "transparent", "#12345678",
  "blue", "darkolivegreen", "chartreuse3", "#ABCDEF", "white", "black",
  "steelblue", "#0000FF80", "NA", "", "nonsense", NA_character_,
  factor("red"), 5
)

one <- function() {
  lapply(colors, function(col) {
    r <- try_val(pretty_color(col))
    if (identical(r, "__error__")) return("__error__")
    list(value = as.character(r), alt = attr(r, "alt"))
  })
}

run_proof("pretty_color", one)
