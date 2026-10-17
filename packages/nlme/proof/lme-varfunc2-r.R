.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

# Newly supported lme variance-function cases on the Orthodont data:
#   fixed:   varPower / varExp with the parameter fixed (no free variance parameter)
#   fitted:  default covariate fitted(.) (varPower(), varExp(), varConstPower()), apVar off
#   apVar:   varPower(~age) with apVar on; the apVar matrix is appended to its block
# Per case the output is fixef, sigma, logLik, varFix, ranef, fitted (level 0:1),
# residuals (level 0:1), and for the apVar case also as.vector(apVar).
# The nlminb limits are raised as in lme-varfunc-r.R.
CTRL_NOAP <- lmeControl(apVar = FALSE, msMaxIter = 200, msMaxEval = 400)
CTRL_AP <- lmeControl(apVar = TRUE, msMaxIter = 200, msMaxEval = 400)

cases <- list(
  varPowerFixed = function() lme(distance ~ age, data = Orthodont,
                                 weights = varPower(form = ~age, fixed = 0.5), control = CTRL_NOAP),
  varExpFixed = function() lme(distance ~ age, data = Orthodont,
                               weights = varExp(form = ~age, fixed = 0.1), control = CTRL_NOAP),
  varPowerFitted = function() lme(distance ~ age, data = Orthodont,
                                  weights = varPower(), control = CTRL_NOAP),
  varExpFitted = function() lme(distance ~ age, data = Orthodont,
                                weights = varExp(), control = CTRL_NOAP),
  varConstPowerFitted = function() lme(distance ~ age, data = Orthodont,
                                       weights = varConstPower(), control = CTRL_NOAP),
  varPowerApVar = function() lme(distance ~ age, data = Orthodont,
                                 weights = varPower(form = ~age), control = CTRL_AP)
)

NLMINB_LOG <- list()
record_nlminb <- function(rv) {
  NLMINB_LOG[[length(NLMINB_LOG) + 1L]] <<- c(rv$iterations, rv$evaluations)
}

# Returns one list element per case: values and the nlminb calls it made.
one <- function() {
  out <- list()
  for (name in names(cases)) {
    before <- length(NLMINB_LOG)
    fm <- cases[[name]]()
    calls <- NLMINB_LOG[seq_len(length(NLMINB_LOG) - before) + before]
    values <- c(
      fixef(fm), fm$sigma, as.numeric(logLik(fm)), as.vector(fm$varFix),
      as.vector(as.matrix(ranef(fm))),
      as.vector(fitted(fm, level = 0:1)),
      as.vector(residuals(fm, level = 0:1))
    )
    if (name == "varPowerApVar") values <- c(values, as.vector(fm$apVar))
    out[[name]] <- list(values = values, calls = calls)
  }
  out
}

ns <- asNamespace("nlme")
invisible(trace("nlminb", where = ns, print = FALSE, exit = quote(record_nlminb(returnValue()))))
NLMINB_LOG <- list()
value <- one()
invisible(untrace("nlminb", where = ns))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

# Per case: the value vector and the nlminb calls as [iterations, fn evals, grad evals].
case_values <- unlist(lapply(value, `[[`, "values"))
case_lengths <- vapply(value, function(case) length(case$values), 1L)
call_json <- vapply(value, function(case) {
  calls <- vapply(case$calls, function(v) paste0("[", paste(as.integer(v), collapse = ","), "]"), "")
  paste0("[", paste(calls, collapse = ","), "]")
}, "")
cat(sprintf(
  "{\"value\":[%s],\"lengths\":[%s],\"iterations\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", case_values), collapse = ","),
  paste(case_lengths, collapse = ","),
  paste(call_json, collapse = ","),
  median(elapsed) * 1000
))
