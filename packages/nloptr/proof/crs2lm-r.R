.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nloptr))

one <- function() {
  rbf <- function(x) (1 - x[1])^2 + 100 * (x[2] - x[1]^2)^2
  S <- crs2lm(c(0, 0), rbf, lower = c(-3, -3), upper = c(3, 3), ranseed = 10L, maxeval = 200L, xtol_rel = 1e-6)
  c(S$par, S$value, S$iter, S$convergence)
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
