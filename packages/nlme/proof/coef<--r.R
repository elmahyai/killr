.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data <- data.frame(
    y = 1:6,
    x = c(1.2, 2.5, 3.1, 4.0, 5.5, 6.3)
  )
  vf <- varPower(0.35, form = ~x)
  vf <- Initialize(vf, data)
  coef(vf) <- 0.6
  vf_part <- c(
    as.vector(coef(vf, unconstrained = TRUE)),
    as.vector(coef(vf, unconstrained = TRUE, allCoef = TRUE)),
    as.vector(varWeights(vf))
  )

  pd1 <- pdMat(diag(1:4), pdClass = "pdDiag")
  coef(pd1) <- log(1:4)
  pd_part <- as.vector(coef(pd1))

  cs1 <- corIdent(form = ~ 1 | Subject)
  coef(cs1) <- 999
  ident_flag <- 1

  c(vf_part, pd_part, ident_flag)
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
