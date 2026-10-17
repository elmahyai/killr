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
  tryCatch(with_progress({
  p <- progressor(steps = 2, on_exit = FALSE)
  p()
  p()
}, handlers = handler_rstudio(enable = TRUE), enable = TRUE, interval = 0, delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character()), error = function(e) conditionMessage(e))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"message":%s,"median_ms":%.17g}\n', json_str(value), median(elapsed) * 1000))
