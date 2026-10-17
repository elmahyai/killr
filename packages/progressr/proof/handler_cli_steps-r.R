.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)

json_str <- function(s) {
  if (is.null(s)) return("null")
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
    if (cp < 32 || cp == 127) return(sprintf("\\u%04x", cp))
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

ids <- character()
invisible(trace(cli::cli_progress_bar, exit = function() {
  val <- returnValue()
  ids <<- c(ids, if (length(val) == 1 && !is.na(val) && grepl("^cli-", val)) "id" else "other")
}, print = FALSE))
on.exit(untrace(cli::cli_progress_bar), add = TRUE)

one <- function() {
  ids <<- character()
  handler <- handler_cli(type = "steps", clear = FALSE, enable = TRUE)
  err <- cap({
    with_progress({
      p <- progressor(steps = 4, on_exit = FALSE)
      for (i in 1:4) p(message = paste0("m", i))
    }, handlers = handler, enable = TRUE, interval = 0,
       delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  })
  sprintf(
    '{"called":%s,"id":%s,"err":%s}',
    if (length(ids) > 0) "true" else "false",
    json_str(if (length(ids)) ids[[1]] else ""),
    json_str(err)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sub("}$", "", value))
cat(sprintf(',"median_ms":%.17g}\n', median(elapsed) * 1000))
