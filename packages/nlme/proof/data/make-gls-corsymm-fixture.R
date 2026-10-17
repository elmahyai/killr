## Writes gls-orthodont-corSymm.json: the R fit used by proof/intervals-corsymm-*.R.
## Run once: Rscript proof/data/make-gls-corsymm-fixture.R  (from packages/nlme)
suppressPackageStartupMessages(library(nlme))
library(jsonlite)

d <- read.csv("proof/data/gls-orthodont.csv", stringsAsFactors = FALSE)
d$Sex <- factor(d$Sex, levels = c("Male", "Female"))
d$Subject <- factor(d$Subject)
d <- d[order(as.character(d$Subject), d$age), ]
rownames(d) <- NULL

fm <- gls(distance ~ age + Sex, d, correlation = corSymm(form = ~ 1 | Subject))
ap <- fm$apVar
iv <- intervals(fm, level = 0.95, which = "all")

out <- list(
  N = fm$dims$N, p = fm$dims$p, REML = fm$dims$REML,
  sigma = fm$sigma,
  logLik = as.numeric(logLik(fm)),
  coefficients = as.numeric(coef(fm)),
  coef_names = names(coef(fm)),
  varBeta = as.numeric(fm$varBeta),
  corSymm_unconstrained = as.numeric(as.vector(fm$modelStruct$corStruct)),
  apVar = as.numeric(ap),
  apVar_dim = dim(ap),
  apVar_Pars = as.numeric(attr(ap, "Pars")),
  apVar_natural = attr(ap, "natural"),
  intervals_coef = as.numeric(iv$coef),
  intervals_corStruct = as.numeric(iv$corStruct),
  intervals_sigma = as.numeric(iv$sigma),
  intervals_corStruct_names = rownames(iv$corStruct),
  intervals_corStruct_dim = dim(iv$corStruct)
)
## Numbers are written with 17 significant digits so that the round trip is exact.
## jsonlite writes at most 15, which moves the fixed inputs by about 1e-15.
num <- function(x) sprintf("%.17g", as.numeric(x))
arr <- function(x) paste0("[", paste(num(x), collapse = ","), "]")
sarr <- function(x) paste0("[", paste0("\"", as.character(x), "\"", collapse = ","), "]")
fields <- c(
  sprintf("\"N\":%d", out$N), sprintf("\"p\":%d", out$p), sprintf("\"REML\":%d", out$REML),
  sprintf("\"sigma\":%s", num(out$sigma)), sprintf("\"logLik\":%s", num(out$logLik)),
  paste0("\"coefficients\":", arr(out$coefficients)),
  paste0("\"coef_names\":", sarr(out$coef_names)),
  paste0("\"varBeta\":", arr(out$varBeta)),
  paste0("\"corSymm_unconstrained\":", arr(out$corSymm_unconstrained)),
  paste0("\"apVar\":", arr(out$apVar)),
  paste0("\"apVar_dim\":", arr(out$apVar_dim)),
  paste0("\"apVar_Pars\":", arr(out$apVar_Pars)),
  paste0("\"apVar_natural\":", tolower(as.character(out$apVar_natural))),
  paste0("\"intervals_coef\":", arr(out$intervals_coef)),
  paste0("\"intervals_corStruct\":", arr(out$intervals_corStruct)),
  paste0("\"intervals_sigma\":", arr(out$intervals_sigma)),
  paste0("\"intervals_corStruct_names\":", sarr(out$intervals_corStruct_names)),
  paste0("\"intervals_corStruct_dim\":", arr(out$intervals_corStruct_dim))
)
writeLines(paste0("{", paste(fields, collapse = ",\n"), "}"), "proof/data/gls-orthodont-corSymm.json")
