.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# User-defined correlation class (the ape / covBM pattern): correlation exp(-theta * (t_i - t_j)^2).
# It supplies corMatrix only, so recalc() reaches the generic recalc.corStruct.
corToy <- function(value, form = ~ t | Subject) {
  structure(as.double(value), formula = form, fixed = FALSE, class = c("corToy", "corStruct"))
}

corMatrix.corToy <- function(object, covariate = getCovariate(object), corr = TRUE, ...) {
  # corr = FALSE is the transpose inverse square root; the default corMatrix.corStruct builds it
  # from corMatrix(object) with corr = TRUE. logLik() reaches it through logDet().
  if (!corr) return(NextMethod())
  theta <- as.numeric(object)
  lapply(covariate, function(t) {
    d <- outer(t, t, "-")
    exp(-theta * d^2)
  })
}

# Same class with a user recalc method. It delegates with NextMethod(), so dispatch goes
# recalc.corToyUser -> (no recalc.corToy) -> recalc.corStruct, the generic path.
corToyUser <- function(value, form = ~ t | Subject) {
  structure(corToy(value, form), class = c("corToyUser", "corToy", "corStruct"))
}

recalc.corToyUser <- function(object, conLin, ...) NextMethod()

dat_sub <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b"),
  t = c(1, 2, 3, 4, 1, 2, 4)
)
con <- list(Xy = matrix(as.double(1:14), 7, 2), logLik = 0.5)

pair <- function(object, conLin) list(object = object, conLin = conLin)

# One setup per case: the recalc inputs are built here, outside the timer.
cases <- list(
  corToy = function() list(
    pair(Initialize(corToy(0.4, ~ t | Subject), dat_sub), con),
    pair(Initialize(corToy(0.15, ~ t | Subject), dat_sub), con)
  ),
  corToyUser = function() list(
    pair(Initialize(corToyUser(0.25, ~ t | Subject), dat_sub), con)
  )
)

# Column-major Xy followed by logLik, for each pair in order.
run_pairs <- function(pairs) {
  unlist(lapply(pairs, function(p) {
    r <- recalc(p$object, p$conLin)
    c(as.vector(r$Xy), as.numeric(r$logLik))
  }))
}

parts <- character(0)
for (name in names(cases)) {
  pairs <- cases[[name]]()
  value <- run_pairs(pairs)
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    run_pairs(pairs)
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  parts <- c(parts, sprintf(
    "\"%s\":{\"value\":[%s],\"median_ms\":%.17g}",
    name,
    paste(sprintf("%.17g", value), collapse = ","),
    median(elapsed) * 1000
  ))
}
cat("{", paste(parts, collapse = ","), "}\n", sep = "")
