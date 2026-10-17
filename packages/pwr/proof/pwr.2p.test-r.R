suppressPackageStartupMessages(library(pwr))
one <- function() {
  pwr.2p.test(h=0.3, n=80, sig.level=0.05, alternative="greater")$power
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
