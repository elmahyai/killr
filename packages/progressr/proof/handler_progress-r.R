.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)
options(width = 80)

json_str <- function(s) {
  s <- enc2utf8(paste(as.character(s), collapse = ""))
  chars <- strsplit(s, "", fixed = TRUE)[[1]]
  if (length(chars) == 0) return('""')
  parts <- vapply(chars, function(ch) {
    cp <- utf8ToInt(ch)
    if (length(cp) != 1) return(ch)
    if (cp == 34) return('\\"')
    if (cp == 92) return("\\\\")
    if (cp == 10) return("\\n")
    if (cp == 13) return("\\r")
    if (cp == 9) return("\\t")
    ch
  }, character(1))
  paste0('"', paste(parts, collapse = ""), '"')
}

cap <- function(expr) {
  path <- tempfile("cap")
  con <- file(path, open = "wt")
  sink(con, type = "message")
  force(expr)
  sink(type = "message")
  close(con)
  n <- file.info(path)$size
  if (is.na(n) || n == 0) return("")
  readChar(path, n, useBytes = TRUE)
}

one <- function() {
  bad <- tryCatch(handler_progress(type = "nope"), error = function(e) conditionMessage(e))
  err <- cap({
    with_progress({
      p <- progressor(steps = 4, on_exit = FALSE)
      for (i in 1:4) p(message = paste0("m", i))
    }, handlers = handler_progress(
         format = ":spin [:bar] :percent :message", width = 40,
         clear = FALSE, enable = TRUE),
       enable = TRUE, interval = 0, delay_terminal = FALSE,
       delay_stdout = FALSE, delay_conditions = character())
  })
  list(bad_type = bad, err = err, nchar = nchar(err))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"bad_type":%s,"err":%s,"nchar":%s,"median_ms":%.17g}\n',
  json_str(value$bad_type), json_str(value$err),
  sprintf("%.17g", value$nchar), median(elapsed) * 1000
))
