.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## gls with correlation = corSymm(form = ~ 1 | group) on two fixed datasets:
##   Orthodont: distance ~ age + Sex, groups Subject
##   Loblolly:  height ~ age, groups Seed
## Each dataset is fitted with glsControl(natural = FALSE) and natural = TRUE.
## R fits the correlation parameters with nlminb (PORT). The Python side runs the
## same PORT kernel (crates/nlminb_port), so these outputs must match at 1e-8.
data(Orthodont, package = "nlme")
## Subject as character: R then sorts groups alphabetically, as the Python side does.
Orthodont$Subject <- as.character(Orthodont$Subject)
data(Loblolly, package = "nlme")
Loblolly$Seed <- as.character(Loblolly$Seed)

## apVar is a message string when the Hessian is not negative definite (Loblolly,
## natural = TRUE): the flag records which case, and the matrix is added only when it is one.
parts <- function(fm) {
  is_msg <- is.character(fm$apVar)
  c(
    as.numeric(coef(fm)), sqrt(diag(fm$varBeta)), fm$sigma, fm$logLik,
    as.numeric(coef(fm$modelStruct$corStruct)), as.numeric(is_msg),
    if (is_msg) numeric(0) else as.numeric(fm$apVar)
  )
}

one <- function() {
  c(
    parts(gls(distance ~ age + Sex, Orthodont,
      correlation = corSymm(form = ~ 1 | Subject),
      control = glsControl(natural = FALSE))),
    parts(gls(distance ~ age + Sex, Orthodont,
      correlation = corSymm(form = ~ 1 | Subject),
      control = glsControl(natural = TRUE))),
    parts(gls(height ~ age, Loblolly,
      correlation = corSymm(form = ~ 1 | Seed),
      control = glsControl(natural = FALSE))),
    parts(gls(height ~ age, Loblolly,
      correlation = corSymm(form = ~ 1 | Seed),
      control = glsControl(natural = TRUE)))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
