## Writes the fixed inputs shared by the gls, glsEstimate, glsApVar, intervals,
## and recalc proofs. Run once from any directory:
##   Rscript packages/nlme/proof/gls-fixtures-r.R
## The R proofs refit the same models in their untimed setup. The Python
## proofs read these files, so they never call R.
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grep("^--file=", args)])
proof_dir <- if (length(script)) dirname(normalizePath(script)) else "packages/nlme/proof"
data_dir <- file.path(proof_dir, "data")
dir.create(data_dir, showWarnings = FALSE, recursive = TRUE)

jnum <- function(x) {
  if (is.na(x)) return("null")
  sprintf("%.17g", x)
}
jvec <- function(x) paste0("[", paste(vapply(as.numeric(x), jnum, ""), collapse = ","), "]")
jint <- function(x) paste0("[", paste(as.integer(x), collapse = ","), "]")
jsc <- function(x) as.character(as.integer(x)[1])
jstr <- function(x) paste0("\"", x, "\"")

## Oats with an AR(1) correlation: the trace captures the arguments that
## gls passes to glsApVar. Those are the fixed inputs of the Oats cases.
data(Oats, package = "nlme")
saved <- new.env()
trace("glsApVar",
      tracer = quote({
        saved$glsSt <- glsSt
        saved$sigma <- sigma
        saved$conLin <- conLin
      }),
      print = FALSE, where = asNamespace("nlme"))
fm <- gls(yield ~ Variety - 1, Oats, correlation = corAR1(form = ~ 1 | Block))
untrace("glsApVar", where = asNamespace("nlme"))

cs <- saved$glsSt$corStruct
dimc <- attr(cs, "Dim")
Xy <- saved$conLin$Xy
oats <- paste0(
  "{",
  "\"sigma\":", jnum(saved$sigma), ",",
  "\"N\":", jsc(saved$conLin$dims$N), ",",
  "\"p\":", jsc(saved$conLin$dims$p), ",",
  "\"REML\":", jsc(saved$conLin$dims$REML), ",",
  "\"xy\":", jvec(as.vector(Xy)), ",",
  "\"xy_names\":[", paste0(jstr(colnames(Xy)), collapse = ","), "],",
  "\"fixed_sigma\":", tolower(as.character(isTRUE(attr(saved$glsSt, "fixedSigma")))), ",",
  "\"cor_formula\":\"~1 | Block\",",
  "\"cor_value\":", jvec(as.vector(unclass(cs))), ",",
  "\"cor_fixed\":", tolower(as.character(isTRUE(attr(cs, "fixed")))), ",",
  "\"dim\":{\"N\":", jsc(dimc$N), ",\"M\":", jsc(dimc$M),
  ",\"maxLen\":", jsc(dimc$maxLen), ",\"sumLenSq\":", jsc(dimc$sumLenSq),
  ",\"len\":", jint(dimc$len), ",\"start\":", jint(dimc$start), "},",
  "\"pmap\":", jint(attr(saved$glsSt, "pmap")), ",",
  "\"pmap_rows\":", jsc(nrow(attr(saved$glsSt, "pmap"))), ",",
  "\"pmap_cols\":", jsc(ncol(attr(saved$glsSt, "pmap"))), ",",
  "\"coef_names\":[", paste0(jstr(names(coef(saved$glsSt))), collapse = ","), "],",
  "\"component_names\":[", paste0(jstr(names(saved$glsSt)), collapse = ","), "],",
  "\"fit\":{",
  "\"coefficients\":", jvec(coef(fm)), ",",
  "\"coef_names\":[", paste0(jstr(names(coef(fm))), collapse = ","), "],",
  "\"varBeta\":", jvec(as.vector(fm$varBeta)), ",",
  "\"sigma\":", jnum(fm$sigma), ",",
  "\"logLik\":", jnum(fm$logLik), ",",
  "\"apVar\":", jvec(as.vector(fm$apVar)), ",",
  "\"apVar_Pars\":", jvec(attr(fm$apVar, "Pars")), ",",
  "\"apVar_natural\":", tolower(as.character(isTRUE(attr(fm$apVar, "natural")))),
  "},",
  "\"apVar_R\":", jvec(as.vector(fm$apVar)), ",",
  "\"Dim_len\":", jint(dimc$len),
  "}"
)
writeLines(oats, file.path(data_dir, "gls-oats-corAR1.json"))

## Orthodont with no correlation or weights: the default gls path.
data(Orthodont, package = "nlme")
orth <- as.data.frame(Orthodont)
orth$Subject <- as.character(orth$Subject)
write.csv(
  data.frame(distance = orth$distance, age = orth$age,
             Sex = as.character(orth$Sex), Subject = orth$Subject),
  file.path(data_dir, "gls-orthodont.csv"), row.names = FALSE
)
g0 <- gls(distance ~ age + Sex, Orthodont)
orth_fix <- paste0(
  "{",
  "\"N\":", jsc(g0$dims$N), ",\"p\":", jsc(g0$dims$p), ",\"REML\":", jsc(g0$dims$REML), ",",
  "\"sex_levels\":[\"Male\",\"Female\"],",
  "\"coefficients\":", jvec(coef(g0)), ",",
  "\"coef_names\":[", paste0(jstr(names(coef(g0))), collapse = ","), "],",
  "\"varBeta\":", jvec(as.vector(g0$varBeta)), ",",
  "\"sigma\":", jnum(g0$sigma), ",",
  "\"logLik\":", jnum(g0$logLik), ",",
  "\"apVar_is_null\":", tolower(as.character(is.null(g0$apVar))),
  "}"
)
writeLines(orth_fix, file.path(data_dir, "gls-orthodont-fit.json"))

## Orthodont groups for the corNatural and varPower recalc cases.
cn <- corNatural(c(0.1, 0.2, 0.3, 0.05, 0.15, 0.25), form = ~ 1 | Subject)
cn <- Initialize(cn, Orthodont)
vp <- varPower(0.35, form = ~ age)
vp <- Initialize(vp, Orthodont)
rec <- paste0(
  "{",
  "\"cn_value\":", jvec(as.vector(unclass(cn))), ",",
  "\"cn_maxCov\":", jsc(attr(cn, "maxCov")), ",",
  "\"cn_dim\":{\"N\":", jsc(attr(cn, "Dim")$N), ",\"M\":", jsc(attr(cn, "Dim")$M),
  ",\"maxLen\":", jsc(attr(cn, "Dim")$maxLen), ",\"sumLenSq\":", jsc(attr(cn, "Dim")$sumLenSq),
  ",\"len\":", jint(attr(cn, "Dim")$len), ",\"start\":", jint(attr(cn, "Dim")$start), "},",
  "\"cn_covariate\":", jint(unlist(attr(cn, "covariate"))), ",",
  "\"vp_values\":", jvec(as.vector(unclass(vp))), ",",
  "\"vp_weights\":", jvec(varWeights(vp)), ",",
  "\"vp_logLik\":", jnum(as.numeric(logLik(vp)))
  , "}"
)
writeLines(rec, file.path(data_dir, "recalc-fixtures.json"))
cat("wrote fixtures to", data_dir, "\n")
