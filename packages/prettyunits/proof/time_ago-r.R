.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.ago.time_ago
# The offsets sit in the middle of each bucket, so the answer does not
# depend on the few milliseconds between the R and Python calls.
offsets <- c(5, 30, 14 * 60, 5 * 3600, 25 * 3600, 5 * 86400, 30 * 86400,
             365 * 86400, 3650 * 86400)

one <- function() {
  now <- Sys.time()
  d <- now - offsets
  list(
    default = time_ago(d),
    short = time_ago(d, format = "short"),
    terse = time_ago(d, format = "terse"),
    bad_format = try_val(time_ago(now, format = "nope"))
  )
}

run_proof("time_ago", one)
