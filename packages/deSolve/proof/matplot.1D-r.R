.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

root <- "/home/ahmed/killr_projects/killr/packages/deSolve"
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

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

build_out <- function() {
  dx <- 100
  N <- 4
  parms <- list(
    dx = dx, v = 1e3, r = 0.05, p = 0.5, O2sat = 300,
    BOD_0 = 1000, O2_0 = 200
  )
  state <- c(rep(200, N), rep(200, N))
  times <- seq(0, 1, by = 0.5)
  ode.1D(
    y = state, times = times, func = O2BOD, parms = parms,
    nspec = 2, names = c("BOD", "O2"), method = "vode"
  )
}

one <- function() {
  out <- build_out()
  pdf(NULL)
  matplot.1D(out, which = 1, ask = FALSE)
  usr <- par("usr")
  dev.off()
  c(usr, as.vector(t(out[, 2:5])))
}

invisible(capture.output({
  out <- build_out()
  svg(file.path(out_dir, "matplot.1D-r.svg"), width = 7, height = 5)
  matplot.1D(out, which = 1, ask = FALSE)
  dev.off()
}))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value_json <- paste0("[", paste(sprintf("%.17g", value), collapse = ","), "]")
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', value_json, median(elapsed) * 1000))
