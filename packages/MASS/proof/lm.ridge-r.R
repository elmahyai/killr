.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")
longley <- datasets::longley
names(longley)[1] <- "y"
one <- function() {
  fit <- lm.ridge(y ~ ., longley, lambda = seq(0, 0.05, 0.01))
  c(
    as.numeric(fit$coef),
    as.numeric(fit$scales),
    as.integer(fit$Inter),
    as.numeric(fit$ym),
    as.numeric(fit$xm),
    as.numeric(fit$GCV),
    fit$kHKB,
    fit$kLW,
    as.numeric(coef(fit))
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
