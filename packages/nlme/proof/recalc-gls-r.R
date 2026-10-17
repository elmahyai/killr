.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## recalc for the structures gls uses. Three fixed inputs, one timed call each:
##   A. corAR1 on the Oats gls fit (conLin captured from the gls fit, unwhitened Xy)
##   B. corNatural on Orthodont (6 unconstrained values, maxCov = 4)
##   C. varPower on Orthodont (age covariate)
## corARMA is not included: its recalc needs ARMA_recalc, which no crate exports.
saved <- new.env()
trace("glsApVar",
      tracer = quote({
        saved$glsSt <- glsSt
        saved$conLin <- conLin
      }),
      print = FALSE, where = asNamespace("nlme"))
data(Oats, package = "nlme")
invisible(gls(yield ~ Variety - 1, Oats, correlation = corAR1(form = ~ 1 | Block)))
untrace("glsApVar", where = asNamespace("nlme"))

data(Orthodont, package = "nlme")
X <- model.matrix(distance ~ age + Sex, Orthodont)
conOrth <- list(
  Xy = cbind(X, distance = Orthodont$distance),
  dims = list(N = nrow(Orthodont), p = ncol(X), REML = 1L),
  logLik = 0, sigma = 0, fixedSigma = FALSE
)
cn <- Initialize(corNatural(c(0.1, 0.2, 0.3, 0.05, 0.15, 0.25), form = ~ 1 | Subject), Orthodont)
vp <- Initialize(varPower(0.35, form = ~ age), Orthodont)

recal <- function(gls_st, con) {
  r <- recalc(gls_st, con)
  c(as.vector(r$Xy), as.numeric(r$logLik))
}

one <- function() {
  c(
    recal(saved$glsSt, saved$conLin),
    recal(glsStruct(corStruct = cn), conOrth),
    recal(glsStruct(varStruct = vp), conOrth)
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
