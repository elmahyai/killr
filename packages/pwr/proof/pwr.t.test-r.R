suppressPackageStartupMessages(library(pwr))
one <- function() {
  pwr.t.test(d=2/2.8, n=30, sig.level=0.05, type="two.sample", alternative="two.sided")$power
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
