suppressPackageStartupMessages(library(survival))

one <- function() {
  a <- as.character(Surv(c(1, 2.5, 10, NA), c(1, 0, 1, 1)))
  b <- as.character(Surv(c(0, 1), c(5, 6.25), c(1, 0), type = "counting"))
  d <- as.character(Surv(c(1, 2), c(1, 3), type = "interval2"))
  e <- as.character(Surv(c(1, 2), c(0, 1), type = "left"))
  c(paste(a, collapse = "|"), paste(b, collapse = "|"), paste(d, collapse = "|"), paste(e, collapse = "|"))
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
