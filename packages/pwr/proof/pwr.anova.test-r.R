suppressPackageStartupMessages(library(pwr))
one <- function() {
  pwr.anova.test(f=0.28, k=4, n=20, sig.level=0.05)$power
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
