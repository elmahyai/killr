
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(evaluate))
options(prompt = "> ", continue = "+ ")
json_str <- function(s) {
  s <- enc2utf8(paste(s, collapse = "\n"))
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  paste0("\"", s, "\"")
}
json_val <- function(x) {
  if (is.logical(x)) x <- as.numeric(x)
  if (is.numeric(x)) {
    if (length(x) == 1) return(sprintf("%.17g", as.numeric(x)))
    return(paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]"))
  }
  x <- as.character(x)
  if (length(x) == 1) return(json_str(x[[1]]))
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
one <- function() {
  local({
    local_reproducible_output(width = 40, color = FALSE)
    c(getOption("width"), as.numeric(Sys.getenv("NO_COLOR")))
  })
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
