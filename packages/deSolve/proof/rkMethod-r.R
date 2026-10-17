.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")
json_num <- function(x) {
  x <- as.numeric(x)
  parts <- vapply(x, function(v) if (is.na(v)) "NaN" else sprintf("%.17g", v), character(1))
  paste0("[", paste(parts, collapse = ","), "]")
}
flatten_rkMethod <- function(m) {
  c(
    as.integer(m$varstep),
    if (!is.null(m$FSAL)) as.integer(m$FSAL) else NA_real_,
    if (!is.null(m$implicit)) as.integer(m$implicit) else NA_real_,
    as.vector(m$A),
    m$b1,
    if (!is.null(m$b2)) m$b2 else numeric(0),
    m$c,
    if (!is.null(m[["d"]])) m[["d"]] else numeric(0),
    m$stage,
    m$Qerr,
    if (!is.null(m$densetype)) m$densetype else NA_real_
  )
}
one <- function() {
  flatten_rkMethod(rkMethod("ode45"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
