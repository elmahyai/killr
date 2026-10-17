.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
mod <- function(t, x, parms) {
  with(as.list(c(x, parms)), {
    dx <- r * x[1] * (1 - x[1] / K)
    list(c(dx), prev = timestep(TRUE), curr = timestep(FALSE))
  })
}
out <- rk4(c(N = 0.1), seq(0, 20, 2), mod, c(r = 0.5, K = 100))
cat(
  sprintf(
    '{"prev":%s,"curr":%s}\n',
    json_num(out[, "prev"]),
    json_num(out[, "curr"])
  )
)
