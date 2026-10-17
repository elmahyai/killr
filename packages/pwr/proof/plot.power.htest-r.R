suppressPackageStartupMessages(library(pwr))
one <- function() {
  x <- pwr.t.test(d=0.3, power=0.8, type="two.sample", alternative="two.sided")
  n <- x$n
  n_upper <- max(n * 1.5, n + 30)
  ss <- seq.int(from=10, to=n_upper, by=(n_upper - 10)/20)
  paste(sprintf("%.17g", sapply(ss, function(s) pwr.t.test(n=s, d=0.3, sig.level=x$sig.level, type="two.sample", alternative="two.sided")$power)), collapse=",")
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
