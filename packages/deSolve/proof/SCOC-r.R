.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

Flux <- matrix(
  ncol = 2,
  byrow = TRUE,
  data = c(
    1, 0.654, 11, 0.167, 21, 0.060, 41, 0.070, 73, 0.277, 83, 0.186,
    93, 0.140, 103, 0.255, 113, 0.231, 123, 0.309, 133, 1.127, 143, 1.923,
    153, 1.091, 163, 1.001, 173, 1.691, 183, 1.404, 194, 1.226, 204, 0.767,
    214, 0.893, 224, 0.737, 234, 0.772, 244, 0.726, 254, 0.624, 264, 0.439,
    274, 0.168, 284, 0.280, 294, 0.202, 304, 0.193, 315, 0.286, 325, 0.599,
    335, 1.889, 345, 0.996, 355, 0.681, 365, 1.135
  )
)
parms <- c(k = 0.01)

scocder_value <- function(k, y, depo) {
  c(ydot = -k * y + depo, Mineralisation = k * y, Depo = depo)
}

proof_one <- function() {
  pts <- list(
    c(0.01, 63.00301, 0.654),
    c(0.01, 34.3997631, 0.2205),
    c(0.01, 72.98281, 1.135),
    c(0.02, 10.0, 0.5),
    c(0.005, 100.0, 0.0)
  )
  vapply(
    pts,
    function(p) scocder_value(p[1], p[2], p[3]),
    numeric(3)
  )
}

value <- as.vector(proof_one())

timing_one <- function() {
  SCOC(1:365, parms = parms, Flux = Flux)
}
invisible(timing_one())

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  invisible(timing_one())
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(
  sprintf(
    '{"value":%s,"median_ms":%.17g}\n',
    json_num(value),
    median(elapsed) * 1000
  )
)
