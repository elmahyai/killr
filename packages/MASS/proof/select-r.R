.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")
longley <- datasets::longley
names(longley)[1] <- "y"
one <- function() {
  fit <- lm.ridge(y ~ ., longley, lambda = seq(0, 0.05, 0.01))
  capture.output(select(fit))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
