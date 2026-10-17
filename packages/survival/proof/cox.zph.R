suppressPackageStartupMessages(library(survival))

one <- function() {
  fit <- coxph(Surv(futime, fustat) ~ age + ecog.ps, data = ovarian, x = TRUE, model = TRUE)
  zp <- cox.zph(fit)
  c(
    sprintf("%.17g", zp$table[, "chisq"]),
    sprintf("%.17g", zp$table[, "df"]),
    sprintf("%.17g", zp$table[, "p"]),
    sprintf("%.17g", sum(zp$y)),
    sprintf("%.17g", sum(zp$var))
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
