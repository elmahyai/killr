.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.numbers.pretty_num
y <- c(NA, NaN, -1, 0, 1e-25, 1.3333e-5, 999, 1000, 999950, 1e6, -2.5e9,
       1e30, 1e-30, 0.5, 1e-300, -1e-17)

one <- function() {
  list(
    default = pretty_num(y),
    nopad = pretty_num(y, style = "nopad"),
    six = pretty_num(y, style = "6"),
    docs = pretty_num(c(1337, 1.3333e-5, 13333337, 1333333337, 133333333337)),
    inf_default = try_val(pretty_num(c(Inf, -Inf))),
    single = pretty_num(1337)
  )
}

run_proof("pretty_num", one)
