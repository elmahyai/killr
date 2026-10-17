.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

chain <- function(t, y, parms) {
  k <- parms[["k"]]
  list(-k * y)
}

y <- rep(1, 5)
times <- seq(0, 2, by = 0.5)
parms <- list(k = 0.3)

one <- function() {
  out <- ode.band(
    y = y,
    times = times,
    func = chain,
    parms = parms,
    nspec = 1,
    dimens = 5,
    bandup = 1,
    banddown = 1,
    method = "vode",
    rtol = 1e-8,
    atol = 1e-8
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
