.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  set.seed(4242)
  type1 <- c(0.8, 0.8, 0.2, 0.2)
  type2 <- c(0.2, 0.2, 0.8, 0.8)
  x <- matrix(runif(400), nrow = 100)
  x[1:50, ] <- t(t(x[1:50, ]) < type1) * 1
  x[51:100, ] <- t(t(x[51:100, ]) < type2) * 1
  fit <- lca(x, 2, niter = 25, matchdata = TRUE)
  c(
    as.numeric(fit$classprob),
    as.numeric(fit$p),
    as.numeric(fit$matching),
    fit$logl,
    fit$loglsat,
    fit$chisq,
    fit$lhquot,
    fit$bic,
    fit$bicsat,
    fit$n,
    fit$np
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
