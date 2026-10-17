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
    if (ch == "\a") return("\\u0007")
    ch
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}
json_bool <- function(x) if (isTRUE(x)) "true" else "false"
json_num <- function(x) sprintf("%.17g", as.numeric(x))

read_all <- function(path) {
  n <- file.info(path)$size
  if (is.na(n) || n == 0) return("")
  readChar(path, n, useBytes = TRUE)
}

one <- function() {
  bare <- handler_void()
  out <- tempfile("void")
  con <- file(out, open = "wt")
  sink(con)
  sink(con, type = "message")
  value <- with_progress({
    p <- progressor(steps = 2, on_exit = FALSE)
    p(message = "a")
    p(message = "b")
    6
  }, handlers = handler_void(enable = TRUE), enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  sink(type = "message")
  sink()
  close(con)
  list(
    enable = environment(bare)$enable,
    target = environment(bare)$target,
    intrusiveness = environment(bare)$intrusiveness,
    result = value,
    output = read_all(out)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"enable":%s,"target":%s,"intrusiveness":%s,"result":%s,"output":%s,"median_ms":%.17g}\n',
  json_bool(value$enable), json_str(value$target), json_num(value$intrusiveness),
  json_num(value$result), json_str(value$output), median(elapsed) * 1000
))
