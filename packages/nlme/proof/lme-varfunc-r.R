.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

# One weighted lme fit per variance class, all on the Orthodont data (apVar off).
# The nlminb limits are raised: varConstPower with the default limits stops at
# "iteration limit reached" in R itself. Per fit the output is fixef, sigma,
# logLik, varFix, ranef, fitted (level 0:1), residuals (level 0:1); the four
# fits are concatenated in the order below.
CTRL <- lmeControl(apVar = FALSE, msMaxIter = 200, msMaxEval = 400)

one <- function() {
  fits <- list(
    varPower = lme(distance ~ age, data = Orthodont,
                   weights = varPower(form = ~age), control = CTRL),
    varExp = lme(distance ~ age, data = Orthodont,
                 weights = varExp(form = ~age), control = CTRL),
    varIdent = lme(distance ~ age, data = Orthodont,
                   weights = varIdent(form = ~1 | Sex), control = CTRL),
    varConstPower = lme(distance ~ age, data = Orthodont,
                        weights = varConstPower(form = ~age), control = CTRL),
    varPowerSex = lme(distance ~ age, data = Orthodont,
                      weights = varPower(form = ~age | Sex), control = CTRL),
    varExpSex = lme(distance ~ age, data = Orthodont,
                    weights = varExp(form = ~age | Sex), control = CTRL)
  )
  unlist(lapply(fits, function(fm) c(
    fixef(fm), fm$sigma, as.numeric(logLik(fm)), as.vector(fm$varFix),
    as.vector(as.matrix(ranef(fm))),
    as.vector(fitted(fm, level = 0:1)),
    as.vector(residuals(fm, level = 0:1))
  )), use.names = FALSE)
}

NLMINB_LOG <- list()
record_nlminb <- function(rv) {
  NLMINB_LOG[[length(NLMINB_LOG) + 1L]] <<- c(rv$iterations, rv$evaluations)
}
ns <- asNamespace("nlme")
invisible(trace("nlminb", where = ns, print = FALSE, exit = quote(record_nlminb(returnValue()))))
value <- one()
invisible(untrace("nlminb", where = ns))
iterations <- paste0("[", paste(vapply(NLMINB_LOG, function(v) paste0("[", paste(as.integer(v), collapse = ","), "]"), ""), collapse = ","), "]")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"iterations\":%s,\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  iterations,
  median(elapsed) * 1000
))
