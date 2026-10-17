.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}
subj <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c")
)

one <- function() {
  a <- Initialize(corNatural(c(0.3, 0.1, 0.2, 0.05, 0.1, 0.25), form = ~ 1 | Subject), subj)
  b <- Initialize(corNatural(form = ~ 1 | Subject), subj)
  c(
    as.vector(a), attr(a, "maxCov"), as.vector(corFactor(a)), as.vector(logDet(a)),
    as.vector(coef(a, unconstrained = FALSE)),
    as.vector(b), attr(b, "maxCov"), as.vector(corFactor(b)), as.vector(logDet(b))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
