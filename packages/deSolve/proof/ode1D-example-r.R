.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))

O2BOD <- function(t, state, pars) {
  N <- length(state) / 2
  BOD <- state[1:N]
  O2 <- state[(N + 1):(2 * N)]
  dx <- pars[["dx"]]
  v <- pars[["v"]]
  r <- pars[["r"]]
  p <- pars[["p"]]
  O2sat <- pars[["O2sat"]]
  BOD_0 <- pars[["BOD_0"]]
  O2_0 <- pars[["O2_0"]]
  FluxBOD <- v * c(BOD_0, BOD)
  FluxO2 <- v * c(O2_0, O2)
  BODrate <- r * BOD
  dBOD <- -diff(FluxBOD) / dx - BODrate
  dO2 <- -diff(FluxO2) / dx - BODrate + p * (O2sat - O2)
  list(c(dBOD, dO2))
}

dx <- 100
N <- length(seq(dx / 2, 400, by = dx))
parms <- list(
  dx = dx, v = 1e3, r = 0.05, p = 0.5, O2sat = 300,
  BOD_0 = 1000, O2_0 = 200
)
state <- c(rep(200, N), rep(200, N))
times <- seq(0, 1, by = 0.25)
out <- ode.1D(
  y = state, times = times, func = O2BOD, parms = parms,
  nspec = 2, names = c("BOD", "O2"), method = "vode"
)
print(out[c(1, 3, 5), c(1, 2, N + 2)])
