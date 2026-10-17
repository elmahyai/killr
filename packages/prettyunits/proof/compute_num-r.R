.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.numbers.compute_num
y <- c(NA, NaN, -1, 0, 1e-25, 1.3333e-5, 999, 1000, 999950, 1e6, -2.5e9,
       1e30, 1e-30, Inf, -Inf, 0.5, 1e-300, -1e-17)

one <- function() {
  a <- compute_num(y)
  b <- compute_num(y, smallest_prefix = "m")
  list(
    default = list(amount = a$amount, prefix = a$prefix, negative = a$negative),
    m = list(amount = b$amount, prefix = b$prefix, negative = b$negative)
  )
}

run_proof("compute_num", one)
