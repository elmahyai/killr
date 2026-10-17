.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nloptr))

one <- function() {
  eval_f <- function(x) 100 * (x[2] - x[1] * x[1])^2 + (1 - x[1])^2
  eval_grad_f <- function(x) c(-400 * x[1] * (x[2] - x[1] * x[1]) - 2 * (1 - x[1]), 200 * (x[2] - x[1] * x[1]))
  res <- nloptr(c(-1.2, 1), eval_f, eval_grad_f, opts = list(algorithm = "NLOPT_LD_LBFGS", xtol_rel = 1e-8))
  c(res$solution, res$objective, res$iterations, res$status)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
if (is.character(value) && length(value) == 1) {
  esc <- gsub("\\", "\\\\", value, fixed = TRUE)
  esc <- gsub("\"", "\\\"", esc, fixed = TRUE)
  esc <- gsub("\n", "\\n", esc, fixed = TRUE)
  esc <- gsub("\t", "\\t", esc, fixed = TRUE)
  encoded <- paste0("\"", esc, "\"")
} else if (is.logical(value) && length(value) == 1) {
  encoded <- if (isTRUE(value)) "true" else "false"
} else {
  encoded <- json_num(value)
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encoded, median(elapsed) * 1000))
