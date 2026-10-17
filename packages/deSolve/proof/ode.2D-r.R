.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

react2d <- function(t, state, parms) {
  nx <- parms[["nx"]]
  ny <- parms[["ny"]]
  nn <- nx * ny
  a <- state[seq_len(nn)]
  b <- state[(nn + 1):(2 * nn)]
  r <- parms[["r"]]
  list(c(-r * a, -0.5 * r * b))
}

nx <- 2
ny <- 2
nn <- nx * ny
parms <- list(nx = nx, ny = ny, r = 0.7)
state <- c(rep(1.0, nn), rep(2.0, nn))
times <- seq(0, 1, by = 0.5)

one <- function() {
  out <- ode.2D(
    y = state,
    times = times,
    func = react2d,
    parms = parms,
    nspec = 2,
    dimens = c(nx, ny),
    names = c("A", "B"),
    method = "lsodes",
    rtol = 1e-8,
    atol = 1e-8,
    lrw = 300
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
