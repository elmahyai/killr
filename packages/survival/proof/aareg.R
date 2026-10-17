suppressPackageStartupMessages(library(survival))

serialize_aareg <- function(fit) {
  c(
    sprintf("%.17g", fit$times),
    sprintf("%.17g", fit$nrisk),
    sprintf("%.17g", fit$coefficient),
    sprintf("%.17g", fit$tweight),
    sprintf("%.17g", fit$test.statistic),
    sprintf("%.17g", fit$test.var)
  )
}

options(na.action = na.exclude)

one <- function() {
  test1 <- data.frame(
    time = c(4, 3, 1, 1, 2, 2, 3),
    status = c(1, NA, 1, 0, 1, 1, 0),
    x = c(0, 2, 1, 1, 1, 0, 0)
  )
  fit <- aareg(Surv(time, status) ~ x, test1)
  serialize_aareg(fit)
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
