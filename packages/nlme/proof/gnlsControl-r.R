.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  x <- gnlsControl()
  c(
    x$maxIter, x$nlsMaxIter, x$msMaxIter, x$minScale, x$tolerance, x$nlsTol, x$msTol,
    as.numeric(x$returnObject), as.numeric(x$msVerbose), as.numeric(x$apVar),
    if (x$opt == "nlminb") 0 else 1,
    x$.relStep, x$minAbsParApVar, x$sigma
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
