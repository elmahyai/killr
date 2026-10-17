.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(prettyunits))  # 1.2.0
.here <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.here, "harness.R"))

# Python: prettyunits.time.pretty_ms
ms <- c(0, 0.4, 999.9999, 1000, 1337, 13370, 133700, 1337000, 1337000000, -5,
        NA, NaN, 2 * 86400000 + 5 * 3600000 + 7 * 60000 + 1234.5, 59999.96,
        3599999.9, 86400000, 1, 6.445565082178481e+20, -3.231135713311895e-24)

one <- function() {
  list(
    default = pretty_ms(ms),
    compact = pretty_ms(ms, compact = TRUE)
  )
}

run_proof("pretty_ms", one)
