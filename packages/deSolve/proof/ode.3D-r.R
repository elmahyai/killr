.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

react3d <- function(t, state, parms) {
  list(-parms[["r"]] * state)
}

dims <- c(2, 2, 2)
state <- rep(1.0, 8)
times <- seq(0, 1, by = 0.5)
parms <- list(r = 0.5)

one <- function() {
  out <- ode.3D(
    y = state,
    times = times,
    func = react3d,
    parms = parms,
    nspec = 1,
    dimens = dims,
    method = "lsodes",
    rtol = 1e-8,
    atol = 1e-8,
    lrw = 800
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
