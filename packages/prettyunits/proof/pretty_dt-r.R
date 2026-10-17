.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.time.pretty_dt
dt <- as.difftime(c(1000, 0, 0.5, 59.99, 3600, 86400 * 3 + 5, NA, NaN, -90,
                    1e9, 1337, 0.9999, 2.5), units = "secs")
dtm <- as.difftime(c(2, 1.5, 0), units = "mins")

one <- function() {
  list(
    default = pretty_dt(dt),
    compact = pretty_dt(dt, compact = TRUE),
    mins = pretty_dt(dtm),
    mins_compact = pretty_dt(dtm, compact = TRUE),
    days = pretty_dt(as.difftime(2, units = "days")),
    not_difftime = try_val(pretty_dt(1000))
  )
}

run_proof("pretty_dt", one)
