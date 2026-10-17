suppressPackageStartupMessages(library(pwr))
one <- function() {
  prob <- matrix(c(0.225, 0.125, 0.125, 0.125, 0.16, 0.16, 0.04, 0.04), nrow=2, byrow=TRUE)
  ES.w2(prob)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
if (is.character(value)) cat(value, "\n", sep="") else cat(sprintf("%.17g\n", value))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
