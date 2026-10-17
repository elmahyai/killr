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
    ch
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}

one <- function() {
  lines <- character()
  handler <- make_progression_handler("rec", reporter = list(
    update = function(config, state, progression, ...) {
      msg <- gsub("\n", "", paste(conditionMessage(progression), collapse = ""), fixed = TRUE)
      if (nzchar(msg)) lines <<- c(lines, msg)
    }
  ), enable = TRUE, target = "file", interval = 0)
  value <- withCallingHandlers({
    with_progress({
      slow_sum_p(1:3, delay = 0, stdout = FALSE, message = TRUE, sticky = FALSE, progress = TRUE)
    }, handlers = handler, enable = TRUE, interval = 0,
       delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  }, message = function(m) {
    lines <<- c(lines, gsub("\n", "", paste(conditionMessage(m), collapse = ""), fixed = TRUE))
    invokeRestart("muffleMessage")
  })
  list(value = as.numeric(value), storage = storage.mode(value), lines = lines)
}

ans <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
quoted <- vapply(ans$lines, json_str, "")
cat(sprintf(
  '{"value":%.17g,"storage":"%s","lines":[%s],"median_ms":%.17g}\n',
  ans$value, ans$storage, paste(quoted, collapse = ","), median(elapsed) * 1000
))
