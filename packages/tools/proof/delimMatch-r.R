suppressPackageStartupMessages(library(tools))

one <- function() {
  x <- c("a{bc}d", "a{b{c}d}", "no", "{a%}", "a\\%{b}", "x[y[z]w]")
  paste0(paste(delimMatch(x), collapse=" "), " ", delimMatch("x[y[z]w]", c("[", "]")), "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
