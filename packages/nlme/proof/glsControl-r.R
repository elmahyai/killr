.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

vals <- function(x) {
  c(
    x$maxIter,
    x$msMaxIter,
    x$tolerance,
    x$msTol,
    as.numeric(x$msVerbose),
    as.numeric(x$`singular.ok`),
    as.numeric(x$returnObject),
    as.numeric(x$apVar),
    x$minAbsParApVar,
    x$.relStep,
    as.numeric(x$opt == "nlminb"),
    as.numeric(x$optimMethod == "BFGS"),
    as.numeric(x$natural),
    x$sigma
  )
}

one <- function() {
  a <- glsControl()
  b <- glsControl(
    maxIter = 10, msMaxIter = 20, tolerance = 1e-4, msTol = 1e-5,
    msVerbose = TRUE, singular.ok = TRUE, returnObject = TRUE,
    apVar = FALSE, minAbsParApVar = 0.1, opt = "optim",
    optimMethod = "Nelder-Mead", natural = FALSE, sigma = 2, .relStep = 0.01
  )
  c(vals(a), vals(b))
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
