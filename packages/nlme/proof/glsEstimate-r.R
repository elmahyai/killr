.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed input: the Oats gls fit with corAR1(form = ~ 1 | Block). The last
## glsEstimate call inside gls is captured (conLin still holds the unwhitened Xy),
## and that call is then timed on its own.
saved <- new.env()
trace("glsEstimate",
      tracer = quote({
        saved$glsSt <- object
        saved$conLin <- conLin
      }),
      print = FALSE, where = asNamespace("nlme"))
data(Oats, package = "nlme")
fm <- gls(yield ~ Variety - 1, Oats, correlation = corAR1(form = ~ 1 | Block))
untrace("glsEstimate", where = asNamespace("nlme"))

glsEstimate_fn <- get("glsEstimate", envir = asNamespace("nlme"))

one <- function() {
  val <- glsEstimate_fn(saved$glsSt, conLin = saved$conLin)
  c(
    as.numeric(val$beta),
    val$sigma,
    val$logLik,
    as.numeric(val$varBeta),
    as.numeric(val$fitted),
    as.numeric(val$resid)
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
