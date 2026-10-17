.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.bytes.compute_bytes
x <- c(NA, NaN, -1, 0, 1, 999, 1000, 1e4, 999949, 999950, 1e6, -1e5,
       1.5e9, 2.5e12, 1e18, 1e24, Inf, -Inf)

one <- function() {
  a <- compute_bytes(x)
  b <- compute_bytes(x, smallest_unit = "kB")
  list(
    default = list(amount = a$amount, unit = a$unit, negative = a$negative),
    kB = list(amount = b$amount, unit = b$unit, negative = b$negative)
  )
}

run_proof("compute_bytes", one)
