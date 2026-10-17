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
  bare <- handler_ascii_alert()
  path <- tempfile("al")
  con <- file(path, open = "wt")
  handler <- handler_ascii_alert(file = con, enable = TRUE, intrusiveness = 1)
  with_progress({
    p <- progressor(steps = 4, on_exit = FALSE)
    p(message = "a")
    p(amount = 0, message = "zero")
    p(message = "ding", amount = 0, type = "interrupt", class = "control_progression")
    p(message = "b")
    p(message = "c")
    p(message = "d")
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  close(con)
  target <- environment(bare)$target
  list(
    intrusiveness = environment(bare)$intrusiveness,
    target = target,
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
target_json <- paste0("[", paste(vapply(value$target, json_str, ""), collapse = ","), "]")
cat(sprintf(
  '{"intrusiveness":%s,"target":%s,"text":%s,"median_ms":%.17g}\n',
  json_num(value$intrusiveness), target_json, json_str(value$text),
  median(elapsed) * 1000
))
