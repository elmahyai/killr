.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)

json_str <- function(s) {
  s <- enc2utf8(paste(s, collapse = ""))
  chars <- strsplit(s, "", fixed = TRUE)[[1]]
  if (length(chars) == 0) return('""')
  parts <- vapply(chars, function(ch) {
    if (ch == '"') return('\\"')
    if (ch == "\\") return("\\\\")
    if (ch == "\n") return("\\n")
    if (ch == "\r") return("\\r")
    if (ch == "\t") return("\\t")
    ch
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}

one <- function() {
  err <- tryCatch(
    handler_winprogressbar(enable = TRUE, inputs = list(title = "nope")),
    error = function(e) conditionMessage(e)
  )
  list(error = paste(err, collapse = ""))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"error":%s,"median_ms":%.17g}\n',
  json_str(value$error), median(elapsed) * 1000
))
