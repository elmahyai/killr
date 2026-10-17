suppressPackageStartupMessages(library(survival))

one <- function() {
  a <- survreg.control()
  b <- survreg.control(iter.max = 12)
  c(sprintf("%.17g", a$maxiter), sprintf("%.17g", a$rel.tolerance),
    sprintf("%.17g", a$toler.chol), sprintf("%.17g", a$iter.max),
    sprintf("%.17g", a$debug), sprintf("%.17g", a$outer.max),
    sprintf("%.17g", b$maxiter), sprintf("%.17g", b$iter.max))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
