suppressPackageStartupMessages(library(survival))

one <- function() {
  tdata <- data.frame(
    time = c(1, 2, 2, 2, 3, 4, 4, 4, 5, 2),
    status = c(1, 0, 1, 0, 1, 0, 1, 1, 0, 1),
    x = c(5, 5, 4, 4, 3, 3, 7, 6, 5, 4)
  )
  fit <- survConcordance(Surv(time, status) ~ x, data = tdata)
  stats <- as.vector(fit$stats)
  c(
    sprintf("%.17g", fit$concordance),
    sprintf("%.17g", fit$std.err),
    sprintf("%d", fit$n),
    sprintf("%.17g", stats)
  )
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
