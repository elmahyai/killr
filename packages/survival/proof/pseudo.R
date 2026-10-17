suppressPackageStartupMessages(library(survival))

one <- function() {
  fit1 <- survfit(Surv(time, status) ~ 1, data = survival::lung)
  yhat <- pseudo(fit1, times = c(365, 730))
  c(dim(yhat), as.vector(yhat))
}

fmt <- function(x) {
  vapply(
    x,
    function(z) {
      if (length(z) != 1 || is.na(z)) {
        return("NA")
      }
      sprintf("%.17g", z)
    },
    character(1)
  )
}

value <- fmt(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
