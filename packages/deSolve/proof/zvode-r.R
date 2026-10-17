.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

spin <- function(t, y, parms) {
  list(1i * parms$w * y)
}

one <- function() {
  out <- zvode(
    c(z = 1 + 0i),
    seq(0, 6, by = 2),
    spin,
    list(w = 1.0)
  )
  v <- as.vector(out)
  c(Re(v), Im(v))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
