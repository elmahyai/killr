.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

fields <- c("maxIter", "msMaxIter", "tolerance", "niterEM", "msMaxEval",
            "msTol", "msVerbose", "returnObject", "gradHess", "apVar",
            ".relStep", "minAbsParApVar", "natural", "sigma", "allow.n.lt.q")

one <- function() {
  a <- lmeControl()
  b <- lmeControl(maxIter = 30, msMaxIter = 20, tolerance = 1e-4,
                  niterEM = 10, msMaxEval = 100, msTol = 1e-5,
                  msVerbose = TRUE, returnObject = TRUE, gradHess = FALSE,
                  apVar = FALSE, minAbsParApVar = 0.1, opt = "optim",
                  optimMethod = "Nelder-Mead", natural = FALSE,
                  sigma = 0.5, allow.n.lt.q = TRUE)
  c(
    as.numeric(unlist(a[fields])),
    as.numeric(unlist(b[fields])),
    as.numeric(a$opt == "nlminb"),
    as.numeric(b$opt == "optim"),
    as.numeric(a$optimMethod == "BFGS"),
    as.numeric(b$optimMethod == "Nelder-Mead"),
    length(a),
    length(b)
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
