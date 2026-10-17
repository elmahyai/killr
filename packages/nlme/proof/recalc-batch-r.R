.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

vdata <- data.frame(
  y = 1:9,
  grp = factor(c("A", "A", "B", "B", "C", "C", "A", "B", "C"))
)
subj <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c")
)

one <- function() {
  vf1 <- Initialize(varIdent(value = c(B = 2, C = 3), form = ~ 1 | grp), vdata)
  vf2 <- Initialize(varIdent(value = c(B = 1.5, C = 0.5), form = ~ 1 | grp), vdata)
  conLin <- list(Xy = matrix(as.double(1:18), 9, 2), logLik = 0.5)
  ms <- structure(list(vf1, vf2), class = "modelStruct")
  cc <- Initialize(corCompSymm(0.5, form = ~ 1 | Subject), subj)
  cs <- Initialize(corSymm(c(0.3, 0.1, 0.2, 0.05, 0.1, 0.25), form = ~ 1 | Subject), subj)
  conCor <- list(Xy = matrix(as.double(1:22), 11, 2), logLik = 0.5)
  c(
    as.vector(recalc(vf1, conLin)$Xy),
    as.numeric(recalc(vf1, conLin)$logLik),
    as.vector(recalc(ms, conLin)$Xy),
    as.numeric(recalc(ms, conLin)$logLik),
    as.vector(recalc(cc, conCor)$Xy),
    as.numeric(recalc(cc, conCor)$logLik),
    as.vector(recalc(cs, conCor)$Xy),
    as.numeric(recalc(cs, conCor)$logLik)
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
