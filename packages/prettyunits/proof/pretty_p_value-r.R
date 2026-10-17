.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.p_value.pretty_p_value
x <- c(1, 0, NA, 0.01, 0.0000001, 0.0001, 0.00015, 0.5, 0.99995,
       0.00009999, NaN, 0.123456)

one <- function() {
  list(
    default = pretty_p_value(x),
    minval_05 = pretty_p_value(x, minval = 0.05),
    minval_001 = pretty_p_value(x, minval = 0.001),
    all_na = pretty_p_value(c(NA, NA)),
    out_of_range = try_val(pretty_p_value(c(1.5))),
    bad_minval = try_val(pretty_p_value(0.5, minval = 1))
  )
}

run_proof("pretty_p_value", one)
