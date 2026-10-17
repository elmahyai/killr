.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
Pm <- c(
  BW = 0.182, QP = 4.0, QC = 4.0, VFC = 0.08, VLC = 0.04, VMC = 0.74,
  QFC = 0.05, QLC = 0.15, QMC = 0.32, PLA = 16.17, PFA = 281.48, PMA = 13.3,
  PTA = 16.17, PB = 5.487, MW = 153.8, VMAX = 0.04321671, KM = 0.4027255,
  CONC = 1000, KL = 0.02, RATS = 1.0, VCHC = 3.8
)
y <- c(AI = 21, AAM = 0, AT = 0, AF = 0, AL = 0, CLT = 0, AM = 0)
times <- seq(0, 0.3, by = 0.1)
out <- ccl4model(times, y, Pm, method = "rk4")
print(round(out[, c("time", "CP")], 4))
