.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

parameters <- c(
  maxPhotoSynt = 0.125,
  rMortPHY = 0.001,
  alpha = -0.125 / 150,
  pExudation = 0.0,
  maxProteinSynt = 0.136,
  ksDIN = 1.0,
  minpLMW = 0.05,
  maxpLMW = 0.15,
  minQuotum = 0.075,
  maxStorage = 0.23,
  respirationRate = 0.0001,
  pResp = 0.4,
  catabolismRate = 0.06,
  dilutionRate = 0.01,
  rNCProtein = 0.2,
  inputDIN = 10.0,
  rChlN = 1,
  parMean = 250.0,
  dayLength = 15.0
)

state <- c(
  DIN = 6.0,
  PROTEIN = 20.0,
  RESERVE = 5.0,
  LMW = 1.0
)
names(state) <- c("DIN", "PROTEIN", "RESERVE", "LMW")
outnames <- c(
  "PAR", "TotalN", "PhotoSynthesis",
  "NCratio", "ChlCratio", "Chlorophyll"
)

eval_times <- seq(0, 48, 0.5)

one <- function() {
  vals <- numeric(0)
  for (t in eval_times) {
    out <- DLLfunc(
      func = "aquaphy", times = t, y = state, parms = parameters,
      dllname = "deSolve", initfunc = "iniaqua", nout = 6, outnames = outnames
    )
    vals <- c(vals, as.numeric(out$dy), as.numeric(out$var))
  }
  vals
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  json_num(value), median(elapsed) * 1000
))
