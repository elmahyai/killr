.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Writes the unconstrained structure parameters at R's gls optimum, so the
## glsEstimate proofs for corNatural and varPower start from identical values.
## Run once from packages/nlme: Rscript proof/gls-standin-fixtures-r.R

data(Orthodont, package = "nlme")
## Subject as character: R then sorts groups alphabetically, as the Python side does.
Orthodont$Subject <- as.character(Orthodont$Subject)
fm_nat <- gls(distance ~ age + Sex, Orthodont, correlation = corNatural(form = ~ 1 | Subject))
fm_pow <- gls(distance ~ age + Sex, Orthodont, weights = varPower(form = ~ age))

fmt <- function(x) paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
json <- sprintf(
  "{\"corNatural\":[%s],\"varPower\":[%s]}\n",
  fmt(coef(fm_nat$modelStruct, unconstrained = TRUE)),
  fmt(coef(fm_pow$modelStruct, unconstrained = TRUE))
)
cat(json, file = "proof/data/gls-standin-optimum.json")
cat(json)
