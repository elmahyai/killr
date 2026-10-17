lib <- "/tmp/r-lib"
library(GPArotation, lib.loc = lib)
A <- matrix(c(.8,.1,.2,.6,.2,.3, .1,.7,.2,.2,.8,.2), ncol=2)
data_call <- function() {
  out <- lapply(c("legacy", "bb", "cayley"), function(algorithm) {
    GPArotation::quartimax(A, algorithm=algorithm,
                           fwindow=if (algorithm == "legacy") 1 else 10,
                           maxit=30)
  })
  theta <- seq(0, 2*pi, length.out=101)
  f <- vapply(theta, function(t) {
    L <- A %*% matrix(c(cos(t), sin(t), -sin(t), cos(t)), 2, 2)
    GPArotation:::vgQ.quartimax(L)$f
  }, numeric(1))
  list(out=out, theta=theta, f=f)
}
invisible(data_call())
times <- numeric(20)
for (i in seq_along(times)) {
  t0 <- proc.time()[["elapsed"]]
  value <- data_call()
  times[i] <- (proc.time()[["elapsed"]] - t0) * 1000
}
value <- data_call()
rows <- list(legacy_loadings=as.vector(value$out[[1]]$loadings),
             bb_loadings=as.vector(value$out[[2]]$loadings),
             cayley_loadings=as.vector(value$out[[3]]$loadings),
             landscape=value$f, theta=value$theta)
writeLines(vapply(names(rows), function(k)
  paste(c(k, format(rows[[k]], digits=17, scientific=TRUE)), collapse=","),
  character(1)), "packages/GPArotation/docs/output/plot2fOrthComparison_r.csv")
writeLines(sprintf("%.9f", median(times)),
           "packages/GPArotation/docs/output/plot2fOrthComparison_r_ms.txt")
