.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## glsEstimate on the corNatural structure of Orthodont at R's gls optimum. The last
## glsEstimate call inside gls is captured (conLin still holds the unwhitened Xy),
## and that call is then timed on its own. glsEstimate runs no optimizer in R.
saved <- new.env()
trace("glsEstimate",
      tracer = quote({
        saved$glsSt <- object
        saved$conLin <- conLin
      }),
      print = FALSE, where = asNamespace("nlme"))
data(Orthodont, package = "nlme")
## Subject as character: R then sorts groups alphabetically, as the Python side does.
Orthodont$Subject <- as.character(Orthodont$Subject)
fm <- gls(distance ~ age + Sex, Orthodont, correlation = corNatural(form = ~ 1 | Subject))
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
