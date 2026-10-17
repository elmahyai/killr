.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed input: the glsSt, sigma, and conLin that gls passes to glsApVar for the
## Oats fit with corAR1(form = ~ 1 | Block). The fit runs in the untimed setup;
## only the glsApVar call is timed.
saved <- new.env()
trace("glsApVar",
      tracer = quote({
        saved$glsSt <- glsSt
        saved$sigma <- sigma
        saved$conLin <- conLin
      }),
      print = FALSE, where = asNamespace("nlme"))
data(Oats, package = "nlme")
fm <- gls(yield ~ Variety - 1, Oats, correlation = corAR1(form = ~ 1 | Block))
untrace("glsApVar", where = asNamespace("nlme"))

glsApVar_fn <- get("glsApVar", envir = asNamespace("nlme"))

one <- function() {
  glsApVar_fn(saved$glsSt, saved$sigma, conLin = saved$conLin)
}

res <- one()
value <- c(as.numeric(res), as.numeric(attr(res, "Pars")))
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
