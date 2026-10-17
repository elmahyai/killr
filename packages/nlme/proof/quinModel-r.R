.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

Subject <- c(1, 1, 1, 2, 2, 2)
time <- c(0, 1, 3, 0, 2, 5)
conc <- c(NA, NA, 1.2, NA, NA, 0.85)
dose <- c(100, NA, NA, 150, NA, NA)
interval <- rep(NA_real_, length(time))
lV <- rep(log(50), length(time))
lKa <- rep(log(1.2), length(time))
lCl <- rep(log(2.5), length(time))

one <- function() {
  quinModel(Subject, time, conc, dose, interval, lV, lKa, lCl)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
