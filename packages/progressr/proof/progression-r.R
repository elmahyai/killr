.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(progressr))

json_str <- function(s) {
  s <- enc2utf8(paste(s, collapse = ""))
  chars <- strsplit(s, "", fixed = TRUE)[[1]]
  if (length(chars) == 0) return('""')
  parts <- vapply(chars, function(ch) {
    if (ch == '"') return('\\"')
    if (ch == "\\") return("\\\\")
    if (ch == "\n") return("\\n")
    ch
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}

one <- function() {
  p <- progression(message = "hello", amount = 2, type = "update")
  msg <- conditionMessage(p)
  if (length(msg) == 0) msg <- ""
  list(
    amount = p$amount,
    type = p$type,
    message = paste(msg, collapse = ""),
    class = class(p)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cls <- paste(vapply(value$class, json_str, ""), collapse = ",")
cat(sprintf(
  '{"amount":%.17g,"type":%s,"message":%s,"class":[%s],"median_ms":%.17g}\n',
  value$amount,
  json_str(value$type),
  json_str(value$message),
  cls,
  median(elapsed) * 1000
))
