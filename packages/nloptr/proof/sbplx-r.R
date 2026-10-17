.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nloptr))

one <- function() {
  fphv <- function(x) 100 * (x[3] - 10 * atan2(x[2], x[1]) / (2 * pi))^2 + (sqrt(x[1]^2 + x[2]^2) - 1)^2 + x[3]^2
  S <- sbplx(c(-1, 0, 0), fphv)
  c(S$par, S$value, S$convergence)
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
