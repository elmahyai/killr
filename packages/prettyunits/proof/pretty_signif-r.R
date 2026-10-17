.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.rounding.pretty_signif
x <- c(0, 123456.789, 0.000123456, 1e-7, 9.9999, 99.9999, 999999.5, -0.0004,
       1234567, NA, NaN, Inf, -Inf, 0.1 + 0.2, 5e-324, -0)

one <- function() {
  list(
    default = pretty_signif(x),
    d2 = pretty_signif(x, digits = 2),
    d3_inf = pretty_signif(x, digits = 3, sci_range = Inf),
    d4_sci0 = pretty_signif(x, digits = 4, sci_range = 0, sci_sep = "x10^"),
    vec = pretty_signif(c(0.99999, 9.9999e-5), digits = 3)
  )
}

run_proof("pretty_signif", one)
