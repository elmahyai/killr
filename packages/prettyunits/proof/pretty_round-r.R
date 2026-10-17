.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.rounding.pretty_round
# In R 4.5 a scalar digits argument with two or more values in scientific
# notation fails inside formatC. Those whole-vector calls are wrapped in
# try_val, and the same values are also run one at a time.
x <- c(123.05, 1234567, NA, NaN, Inf, -Inf, -0.0001, 0, 2.5, 3.5, -2.675,
       0.1234567, 99.999, 1e-7, 6.02e23, -0.4)

one <- function() {
  list(
    d3_sci5 = try_val(pretty_round(x, digits = 3, sci_range = 5)),
    d3_sci5_each = vapply(x, function(v) pretty_round(v, digits = 3, sci_range = 5), ""),
    d0 = pretty_round(x),
    d_neg2 = pretty_round(x, digits = -2),
    sci0_x10 = try_val(pretty_round(x, digits = 2, sci_range = 0, sci_sep = "x10^")),
    sci0_x10_each = vapply(x, function(v) pretty_round(v, digits = 2, sci_range = 0, sci_sep = "x10^"), ""),
    vec_digits = pretty_round(c(1.23456, 2.5, 1234.5678), digits = c(2, 0, 1)),
    scalar = pretty_round(3.14159, 2),
    one_sci = pretty_round(1234567, digits = 3, sci_range = 5),
    neg_zero = pretty_round(c(-0.0001, -0.4), digits = 0),
    bad_digits = try_val(pretty_round(c(1, 2, 3), digits = c(1, 2)))
  )
}

run_proof("pretty_round", one)
