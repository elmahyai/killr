suppressPackageStartupMessages(library(survival))

one <- function() {
  tempy <- Surv(c(1, 2, 2, 2, 3, 4, 4, 4, 5, 2), c(1, 0, 1, 0, 1, 0, 1, 1, 0, 1))
  tempx <- c(5, 5, 4, 4, 3, 3, 7, 6, 5, 4)
  fit2 <- concordance(tempy ~ tempx)
  c(
    sprintf("%.17g", fit2$concordance),
    sprintf("%.17g", fit2$count),
    sprintf("%.17g", fit2$var),
    sprintf("%.17g", fit2$cvar),
    sprintf("%d", fit2$n)
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
