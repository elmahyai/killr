suppressPackageStartupMessages(library(survival))

one <- function() {
  sprintf("%d", as.integer(is.na(Surv(c(1, NA, 3), c(1, 1, 0)))))
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
