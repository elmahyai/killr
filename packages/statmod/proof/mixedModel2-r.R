suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
suppressPackageStartupMessages(library(MASS))

collect <- function(out) {
  if (is.null(out$se.varcomp)) {
    return(out$varcomp)
  }
  c(out$varcomp, out$se.varcomp, out$coefficients, out$se.coefficients)
}

one <- function() {
  data(petrol)
  out <- mixedModel2(Y ~ SG + VP + V10 + EP, random = No, data = petrol)
  out2 <- mixedModel2(Y ~ SG + VP + V10 + EP, random = No, data = petrol, only.varcomp = TRUE)
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
