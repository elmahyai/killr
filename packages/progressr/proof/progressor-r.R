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
  seen <- list()
  handler <- make_progression_handler("rec", reporter = list(
    update = function(config, state, progression, ...) {
      msg <- conditionMessage(progression)
      if (length(msg) == 0) msg <- ""
      seen[[length(seen) + 1L]] <<- list(
        type = progression$type,
        amount = progression$amount,
        message = paste(msg, collapse = "")
      )
    }
  ), enable = TRUE, target = "file", interval = 0)
  n <- with_progress({
    p <- progressor(steps = 4)
    p(message = "one")
    p(message = "two")
    p(message = "three")
    p(message = "four")
    length(p)
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  list(length = n, events = seen)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
events <- vapply(value$events, function(ev) {
  sprintf(
    '{"type":%s,"amount":%.17g,"message":%s}',
    json_str(ev$type), ev$amount, json_str(ev$message)
  )
}, "")
cat(sprintf(
  '{"length":%.17g,"events":[%s],"median_ms":%.17g}\n',
  value$length,
  paste(events, collapse = ","),
  median(elapsed) * 1000
))
