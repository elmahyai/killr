.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)

one <- function() {
  c(
    punitroot(1.2836, trend = "nc", statistic = "t"),
    punitroot(1.2836, N = 100, trend = "nc", statistic = "n"),
    punitroot(c(1.2836, -2.5, 0), trend = "c", statistic = "t"),
    punitroot(-3.1, N = 250, trend = "ct", statistic = "t"),
    punitroot(-1.95, N = 50, trend = "ctt", statistic = "n")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
