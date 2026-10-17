.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.ago.vague_dt
# vague_dt takes one interval at a time in R 4.5, so each value is its own call.
secs <- c(-30, 0, 5, 9.9, 10, 30, 44.9, 50, 60, 89, 90, 600, 2699, 2700,
          3599, 5400, 7200, 42 * 3600 - 1, 42 * 3600, 86400, 24 * 3600,
          30 * 86400, 45 * 86400, 335 * 86400, 365 * 86400,
          1.5 * 365.25 * 86400, 3650 * 86400, NA, NaN)

one <- function() {
  out <- list()
  for (f in c("default", "short", "terse")) {
    out[[f]] <- vapply(secs, function(s) {
      try_val(vague_dt(as.difftime(s, units = "secs"), format = f))
    }, "")
  }
  out$empty <- vague_dt(as.difftime(numeric(0), units = "secs"))
  out
}

run_proof("vague_dt", one)
