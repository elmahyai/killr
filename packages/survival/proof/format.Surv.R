suppressPackageStartupMessages(library(survival))

one <- function() {
  s <- Surv(c(1, 2.5, 10, NA), c(1, 0, 1, 1))
  paste0("[", format(s), "]")
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
