.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
parameters <- c(maxPhotoSynt = 0.125, rMortPHY = 0.001, alpha = -0.125 / 150,
  pExudation = 0.0, maxProteinSynt = 0.136, ksDIN = 1.0, minpLMW = 0.05,
  maxpLMW = 0.15, minQuotum = 0.075, maxStorage = 0.23, respirationRate = 0.0001,
  pResp = 0.4, catabolismRate = 0.06, dilutionRate = 0.01, rNCProtein = 0.2,
  inputDIN = 10.0, rChlN = 1, parMean = 250.0, dayLength = 15.0)
state <- c(DIN = 6.0, PROTEIN = 20.0, RESERVE = 5.0, LMW = 1.0)
out <- DLLfunc(
  func = "aquaphy", times = 10, y = state, parms = parameters,
  dllname = "deSolve", initfunc = "iniaqua", nout = 6,
  outnames = c("PAR", "TotalN", "PhotoSynthesis", "NCratio", "ChlCratio", "Chlorophyll")
)
cat("dy:", paste(format(out$dy, digits = 8), collapse = " "), "\n")
cat("var:", paste(format(out$var, digits = 8), collapse = " "), "\n")
