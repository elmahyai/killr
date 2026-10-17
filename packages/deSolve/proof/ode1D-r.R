.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

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
x <- seq(dx / 2, 400, by = dx)
N <- length(x)
parms <- list(
  dx = dx, v = 1e3, r = 0.05, p = 0.5, O2sat = 300,
  BOD_0 = 1000, O2_0 = 200
)
state <- c(rep(200, N), rep(200, N))
times <- seq(0, 1, by = 0.25)

one <- function() {
  out <- ode.1D(
    y = state, times = times, func = O2BOD, parms = parms,
    nspec = 2, names = c("BOD", "O2"), method = "vode",
    rtol = 1e-8, atol = 1e-8
  )
  as.vector(out)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
