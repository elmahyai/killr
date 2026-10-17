.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(magrittr))

root <- "/home/ahmed/killr_projects/killr/packages/magrittr"
dir.create(file.path(root, "docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(
  "pipe_lazy_masking(1:10, sum) returns 55.",
  file.path(root, "docs", "output", "pipe_lazy_masking-r.txt")
)

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
json_str <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0("\"", s, "\"")
}
json_msgs <- function(lines) {
  if (length(lines) == 0) return("[]")
  paste0("[", paste(vapply(lines, json_str, ""), collapse = ","), "]")
}

`%L%` <- pipe_lazy_masking
fsub <- function(a, b) a - b
one <- function() c(1:10 %L% sum, 10 %L% fsub(3), 10 %L% fsub(3, .))

f <- function(x) { message("foo"); x }
g <- function(x) { message("bar"); x }
h <- function(x) { message("baz"); invisible(x) }

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
messages <- capture.output(
  type = "message",
  invisible(NULL %L% f() %L% g() %L% h())
)
cat(sprintf(
  "{\"value\":%s,\"messages\":%s,\"median_ms\":%.17g}\n",
  json_num(value),
  json_msgs(messages),
  median(elapsed) * 1000
))
