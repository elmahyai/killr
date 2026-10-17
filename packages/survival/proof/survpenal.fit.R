.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

# One survpenal.fit call with the default ridge penalty on x1 and x2
# (df = nvar / 2), extreme value distribution, and an estimated scale.
ctrl <- survreg.control()

pack <- function(fit) {
  c(fit$coefficients, fit$var, fit$var2, fit$loglik, fit$iter,
    fit$linear.predictors, fit$df, fit$penalty, fit$score)
}

n <- 200
idx <- seq_len(n)
x1 <- ((idx * 17) %% 10) / 10
x2 <- as.numeric((idx * 13) %% 7) - 3
x3 <- ((idx * 7) %% 5) / 5
time <- 0.5 + ((idx * 31) %% 50) / 10
status <- ifelse((idx %% 4) == 0, 0, 1)
y <- cbind(log(time), status)
x <- cbind(1, x1, x2, x3)
assign <- list(`(Intercept)` = 1L, `ridge(x1, x2)` = 2:3, x3 = 4L)

one <- function() {
  fit <- survival:::survpenal.fit(
    x, y, weights = NULL, offset = NULL, init = NULL,
    controlvals = ctrl, dist = survreg.distributions[["extreme"]],
    scale = 0, nstrat = 1, pcols = list(2:3),
    pattr = list(attributes(ridge(x1, x2))), assign = assign
  )
  pack(fit)
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
