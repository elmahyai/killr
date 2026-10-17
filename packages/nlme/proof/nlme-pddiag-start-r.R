.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
# Diagnostic for structure 3 (pdDiag): R's answer depends on the starting
# values, so a 1e-8 match needs R's nlminb (PORT) path, not only the optimum.
fit_from <- function(start, control = nlmeControl()) {
  fm <- nlme(height ~ SSasymp(age, Asym, R0, lrc), data = Loblolly,
    fixed = Asym + R0 + lrc ~ 1, random = pdDiag(Asym + R0 ~ 1),
    start = start, control = control)
  v <- fm$sigma^2 * pdMatrix(fm$modelStruct$reStruct)$Seed
  c(fixef(fm), v[1, 1], v[2, 2], fm$sigma, as.numeric(logLik(fm)), fm$numIter)
}
starts <- list(
  documented = c(Asym = 103, R0 = -8.5, lrc = -3.3),
  python_answer = c(Asym = 101.47089054188, R0 = -8.6248323846281, lrc = -3.2340769630451)
)
for (nm in names(starts)) {
  out <- fit_from(starts[[nm]])
  cat(sprintf("%-14s %s\n", nm, paste(sprintf("%.10g", out), collapse = " ")))
}
