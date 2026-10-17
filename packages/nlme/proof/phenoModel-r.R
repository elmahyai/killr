.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

Subject <- c(1, 1, 1, 2, 2, 2)
time <- c(0, 1.5, 4, 0, 2, 6)
dose <- c(20, NA, NA, 25, NA, NA)
lCl <- rep(log(0.3), length(time))
lV <- rep(log(10), length(time))

one <- function() {
  phenoModel(Subject, time, dose, lCl, lV)
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
