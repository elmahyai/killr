.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.time.pretty_sec
sec <- c(0, 0.0004, 0.9999, 1.337, 13.37, 133.7, 1337, 13370, 133700,
         1337000, 13370000, -2.5, NA, NaN, 86400 * 1.5, 59.96,
         -2.601329396065269e+16, -1.3009319809382128e-23)

one <- function() {
  list(
    default = pretty_sec(sec),
    compact = pretty_sec(sec, compact = TRUE)
  )
}

run_proof("pretty_sec", one)
