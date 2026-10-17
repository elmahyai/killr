suppressPackageStartupMessages(library(pwr))
one <- function() {
  pwr.f2.test(u=5, v=89, f2=0.1/(1-0.1), sig.level=0.05)$power
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
