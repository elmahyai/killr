suppressPackageStartupMessages(library(survival))

one <- function() {
  link <- blog()
  mu <- c(0.01, 0.2, 0.5, 0.9, 0.99)
  c(link$name, sprintf("%.17g", link$linkfun(mu)))
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
