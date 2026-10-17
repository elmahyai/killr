suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
suppressPackageStartupMessages(library(MASS))

collect <- function(out) {
  if (is.null(out$se.varcomp)) {
    return(out$varcomp)
  }
  c(out$varcomp, out$se.varcomp, out$coefficients, out$se.coefficients)
}

petrol_mats <- function() {
  data(petrol)
  mf <- model.frame(Y ~ SG + VP + V10 + EP, data = petrol)
  mt <- attr(mf, "terms")
  y <- model.response(mf, "numeric")
  X <- model.matrix(mt, mf)
  random <- petrol$No
  lev <- unique.default(random)
  Z <- 0 + (matrix(random, length(random), length(lev)) ==
    t(matrix(lev, length(lev), length(random))))
  list(y = y, X = X, Z = Z)
}

one <- function() {
  m <- petrol_mats()
  out <- mixedModel2Fit(m$y, m$X, m$Z)
  out2 <- mixedModel2Fit(m$y, m$X, m$Z, only.varcomp = TRUE)
  c(collect(out), collect(out2))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
