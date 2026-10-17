suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

one <- function() {
  pbc2 <- na.omit(pbc)
  cfit <- coxph(
    Surv(time, status == 2) ~ age + log(bili) + edema + albumin + stage + copper,
    data = pbc2,
    ties = "breslow"
  )
  out <- royston(cfit)
  c(
    sprintf("%.17g", out["D"]),
    sprintf("%.17g", out["se(D)"]),
    sprintf("%.17g", out["R.D"]),
    sprintf("%.17g", out["R.KO"]),
    sprintf("%.17g", out["R.N"]),
    sprintf("%.17g", out["C.GH"])
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
