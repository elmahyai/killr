suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

one <- function() {
  subcoh <- nwtco$in.subcohort
  selccoh <- with(nwtco, rel == 1 | subcoh == 1)
  ccoh.data <- nwtco[selccoh, ]
  ccoh.data$subcohort <- subcoh[selccoh]
  ccoh.data$histol <- factor(ccoh.data$histol, labels = c("FH", "UH"))
  ccoh.data$stage <- factor(ccoh.data$stage, labels = c("I", "II", "III", "IV"))
  ccoh.data$age <- ccoh.data$age / 12
  fit <- cch(
    Surv(edrel, rel) ~ stage + histol + age,
    data = ccoh.data,
    subcoh = ~subcohort,
    id = ~seqno,
    cohort.size = 4028
  )
  vals <- c(
    as.numeric(fit$coefficients),
    as.numeric(fit$var),
    as.numeric(fit$naive.var)
  )
  sprintf("%.17g", vals)
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
