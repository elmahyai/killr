.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

dat <- data.frame(x = c(0, 1, 0.5, 2), y = c(0, 0, 1, 0.5))
subj <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c")
)
vdat <- data.frame(
  y = 1:9,
  grp = factor(c("A", "A", "B", "B", "C", "C", "A", "B", "C"))
)
pdat <- data.frame(
  y = 1:6,
  x = c(1.2, 2.5, 3.1, 4.0, 5.5, 6.3),
  grp = c("A", "A", "B", "B", "A", "B")
)

one <- function() {
  lin <- Initialize(corLin(2.5, form = ~ x + y, metric = "eu"), dat)
  rat <- Initialize(corRatio(1.8, form = ~ x + y, metric = "eu"), dat)
  sph <- Initialize(corSpher(2.5, form = ~ x + y, metric = "eu"), dat)
  cs0 <- Initialize(corSymm(form = ~ 1 | Subject), subj)
  cs1 <- Initialize(
    corSymm(c(0.3, 0.1, 0.2, 0.05, 0.1, 0.25), form = ~ 1 | Subject),
    subj
  )
  cc0 <- Initialize(corCompSymm(0.5, form = ~ 1 | Subject), subj)
  cc1 <- Initialize(corCompSymm(-0.2, form = ~ 1 | Subject), subj)
  vf1 <- Initialize(varIdent(value = c(B = 2, C = 3), form = ~ 1 | grp), vdat)
  vf2 <- Initialize(
    varIdent(value = c(B = 2), fixed = c(C = 3), form = ~ 1 | grp),
    vdat
  )
  vf3 <- Initialize(varIdent(form = ~ 1), vdat)
  pw1 <- Initialize(varPower(0.35, form = ~ x), pdat)
  pw2 <- Initialize(varPower(value = c(A = 0.3, B = 0.6), form = ~ x | grp), pdat)
  c(
    as.vector(corMatrix(lin)),
    as.vector(corMatrix(rat)),
    as.vector(corMatrix(sph)),
    as.vector(cs0),
    as.vector(coef(cs0, unconstrained = TRUE)),
    as.vector(attr(cs0, "factor")),
    as.vector(attr(cs0, "logDet")),
    attr(cs0, "maxCov"),
    as.vector(cs1),
    as.vector(coef(cs1, unconstrained = FALSE)),
    as.vector(cc0),
    as.vector(coef(cc0, unconstrained = TRUE)),
    attr(cc0, "inf"),
    as.vector(attr(cc0, "factor")),
    as.vector(attr(cc0, "logDet")),
    coef(cc0, unconstrained = FALSE),
    as.vector(cc1),
    attr(cc1, "inf"),
    as.vector(attr(cc1, "factor")),
    as.vector(attr(cc1, "logDet")),
    coef(cc1, unconstrained = FALSE),
    as.vector(coef(vf1, unconstrained = TRUE)),
    as.vector(coef(vf1, unconstrained = FALSE, allCoef = TRUE)),
    as.vector(varWeights(vf1)),
    as.vector(attr(vf1, "logLik")),
    as.vector(coef(vf2, unconstrained = TRUE)),
    as.vector(coef(vf2, unconstrained = FALSE, allCoef = TRUE)),
    as.vector(varWeights(vf2)),
    as.vector(attr(vf2, "logLik")),
    as.vector(coef(vf3, unconstrained = TRUE)),
    as.vector(varWeights(vf3)),
    as.vector(attr(vf3, "logLik")),
    as.vector(coef(pw1, unconstrained = TRUE)),
    as.vector(coef(pw1, unconstrained = TRUE, allCoef = TRUE)),
    as.vector(varWeights(pw1)),
    as.vector(attr(pw1, "logLik")),
    as.vector(coef(pw2, unconstrained = TRUE)),
    as.vector(coef(pw2, unconstrained = TRUE, allCoef = TRUE)),
    as.vector(varWeights(pw2)),
    as.vector(attr(pw2, "logLik"))
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
