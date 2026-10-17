.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(bacteria)
  fit <- glmmPQL(
    y ~ trt + I(week > 2),
    random = ~ 1 | ID,
    family = binomial,
    data = bacteria,
    verbose = FALSE
  )
  c(
    fixef(fit),
    fit$sigma,
    unlist(coef(fit$modelStruct)),
    fitted(fit)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
