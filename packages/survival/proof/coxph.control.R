suppressPackageStartupMessages(library(survival))

one <- function() {
  ctl <- coxph.control()
  c(sprintf("%.17g", ctl$eps), sprintf("%.17g", ctl$toler.chol),
    sprintf("%.17g", ctl$iter.max), sprintf("%.17g", ctl$toler.inf),
    sprintf("%.17g", ctl$outer.max), sprintf("%d", as.integer(ctl$timefix)),
    ctl$survcheckallow)
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
