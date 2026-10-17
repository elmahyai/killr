.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  x <- nlmeControl()
  y <- nlmeControl(maxIter = 100, opt = "nlm", sigma = 2, extraOpt = 3)
  c(
    x$maxIter, x$pnlsMaxIter, x$msMaxIter, x$minScale, x$tolerance, x$niterEM,
    x$pnlsTol, x$msTol, as.numeric(x$returnObject), as.numeric(x$msVerbose),
    as.numeric(x$msWarnNoConv), as.numeric(x$gradHess), as.numeric(x$apVar),
    x$.relStep, x$minAbsParApVar, if (x$opt == "nlminb") 0 else 1,
    as.numeric(x$natural), x$sigma,
    y$maxIter, if (y$opt == "nlm") 1 else 0, y$sigma, y$extraOpt
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
