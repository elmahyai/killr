.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  set.seed(4242)
  x <- matrix(c(
    0, 1, 0, 1,
    1, 0, 1, 0,
    0, 0, 1, 1,
    1, 1, 0, 0,
    0, 1, 1, 0,
    1, 0, 0, 1,
    0, 1, 0, 0,
    1, 0, 1, 1
  ), nrow = 8, byrow = TRUE)
  fit <- lca(x, 2, niter = 15, matchdata = FALSE)
  boot <- bootstrap.lca(fit, nsamples = 4, lcaiter = 12, verbose = FALSE)
  c(
    as.numeric(boot$logl),
    as.numeric(boot$loglsat),
    as.numeric(boot$lratio),
    boot$lratiomean,
    boot$lratiosd,
    boot$lratioorg,
    boot$zratio,
    boot$pvalzratio,
    boot$pvalratio,
    as.numeric(boot$chisq),
    boot$chisqmean,
    boot$chisqsd,
    boot$chisqorg,
    boot$zchisq,
    boot$pvalzchisq,
    boot$pvalchisq,
    boot$nsamples,
    boot$lcaiter
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
