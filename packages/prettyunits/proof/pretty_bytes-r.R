.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.bytes.pretty_bytes
x <- c(NA, NaN, -1, 0, 1, 999, 1000, 1e4, 999949, 999950, 1e6, -1e5,
       1.5e9, 2.5e12, 1e18, 1e24)

one <- function() {
  list(
    default = pretty_bytes(x),
    nopad = pretty_bytes(x, style = "nopad"),
    six = pretty_bytes(x, style = "6"),
    short = pretty_bytes(c(1337, 1.5e6, 0)),
    inf_default = try_val(pretty_bytes(c(Inf, -Inf))),
    single = pretty_bytes(1337)
  )
}

run_proof("pretty_bytes", one)
