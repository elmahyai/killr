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
json_num <- function(x) sprintf("%.17g", as.numeric(x))

read_all <- function(path) {
  n <- file.info(path)$size
  if (is.na(n) || n == 0) return("")
  readChar(path, n, useBytes = TRUE)
}

one <- function() {
  bare <- handler_newline()
  path <- tempfile("nl")
  con <- file(path, open = "wt")
  handler <- handler_newline(file = con, enable = TRUE)
  with_progress({
    p <- progressor(steps = 3, on_exit = FALSE)
    p(message = "a")
    p(amount = 0, message = "still")
    p(type = "hide", class = "control_progression", amount = 0)
    p(type = "unhide", class = "control_progression", amount = 0)
    p(message = "halted", amount = 0, type = "interrupt", class = "control_progression")
    p(message = "b")
    p(message = "c")
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  close(con)
  list(
    intrusiveness = environment(bare)$intrusiveness,
    target = environment(bare)$target,
    text = read_all(path)
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
  '{"intrusiveness":%s,"target":%s,"text":%s,"median_ms":%.17g}\n',
  json_num(value$intrusiveness), json_str(value$target), json_str(value$text),
  median(elapsed) * 1000
))
