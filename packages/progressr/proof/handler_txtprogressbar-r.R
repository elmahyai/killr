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

read_all <- function(path) {
  n <- file.info(path)$size
  if (is.na(n) || n == 0) return("")
  readChar(path, n, useBytes = TRUE)
}

bar_text <- function(style) {
  path <- tempfile("txt")
  con <- file(path, open = "wt")
  handler <- handler_txtprogressbar(style = style, file = con, enable = TRUE, clear = FALSE)
  with_progress({
    p <- progressor(steps = 4, on_exit = FALSE)
    p(message = "one")
    p(message = "two")
    p(message = "three")
    p(message = "four")
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  close(con)
  read_all(path)
}

one <- function() {
  list(style3 = bar_text(3L), style1 = bar_text(1L))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"style3":%s,"style1":%s,"median_ms":%.17g}\n',
  json_str(value$style3), json_str(value$style1), median(elapsed) * 1000
))
