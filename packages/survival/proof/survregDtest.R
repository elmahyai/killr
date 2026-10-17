suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

serialize <- function(x) {
  if (isTRUE(x)) {
    "TRUE"
  } else if (isFALSE(x)) {
    "FALSE"
  } else {
    paste(x, collapse = "|")
  }
}

mycauchy <- list(
  name = "Cauchy",
  init <- function(x, weights, ...) c(median(x), mad(x)),
  density = function(x, parms) {
    temp <- 1 / (1 + x^2)
    cbind(
      .5 + atan(temp) / pi,
      .5 + atan(-temp) / pi,
      temp / pi,
      -2 * x * temp,
      2 * temp^2 * (4 * x^2 * temp - 1)
    )
  },
  quantile = function(p, parms) tan((p - 0.5) * pi),
  deviance = function(...) stop("deviance residuals not defined")
)

one <- function() {
  c(
    serialize(survregDtest(mycauchy, TRUE)),
    serialize(survregDtest(mycauchy, FALSE)),
    serialize(survregDtest(survreg.distributions$gaussian)),
    serialize(survregDtest(survreg.distributions$weibull))
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
