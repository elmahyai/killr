suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

aml <- data.frame(
  time = c(
    9, 13, 13, 18, 23, 28, 31, 34, 45, 48, 161, 5, 5, 8, 8, 12, 16, 23, 27, 30, 33, 43, 45
  ),
  status = c(
    1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1
  ),
  x = c(
    rep("Maintained", 11), rep("Nonmaintained", 12)
  ),
  stringsAsFactors = FALSE
)

aml_na <- aml
aml_na$x[7] <- NA

aml_near <- aml
aml_near$time <- aml$time + ifelse(seq_len(23) %% 2 == 0, 1e-12, 0)

aml_off <- aml
aml_off$p <- (seq_len(23)) / 24

synth <- data.frame(
  time = ((seq_len(60) * 7L) %% 17L) + 1,
  status = as.integer(seq_len(60) %% 4L != 0L),
  grp = c("B", "A", "C")[(seq_len(60) %% 3L) + 1L],
  s = (seq_len(60) %% 2L) + 1,
  z = c("u", "v", "w")[((seq_len(60) %% 5L) %% 3L) + 1L],
  stringsAsFactors = FALSE
)

vals <- function(fit) {
  c(
    as.numeric(fit$n),
    as.numeric(fit$obs),
    as.numeric(fit$exp),
    as.numeric(fit$var),
    as.numeric(fit$chisq),
    as.numeric(fit$pvalue),
    if (!is.null(fit$strata)) as.numeric(fit$strata) else numeric(0)
  )
}

one <- function() {
  out <- c(
    vals(survdiff(Surv(time, status) ~ x, data = aml)),
    vals(survdiff(Surv(time, status) ~ x, data = aml, rho = 1)),
    vals(survdiff(Surv(time, status) ~ x, data = aml, rho = 0.5)),
    vals(survdiff(Surv(time, status) ~ x, data = aml_na)),
    vals(survdiff(Surv(time, status) ~ x, data = aml_near)),
    vals(survdiff(Surv(time, status) ~ grp + strata(s), data = synth)),
    vals(survdiff(Surv(time, status) ~ grp + strata(s, z), data = synth, rho = 1)),
    vals(survdiff(Surv(time, status) ~ grp, data = synth, rho = -1)),
    vals(survdiff(Surv(time, status) ~ offset(p), data = aml_off)),
    vals(survdiff(Surv(time, status) ~ offset(p), data = aml_off, rho = 0.5))
  )
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", value), collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
