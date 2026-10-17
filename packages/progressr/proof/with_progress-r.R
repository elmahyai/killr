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

record <- function(config, state, progression) {
  msg <- conditionMessage(progression)
  if (length(msg) == 0) msg <- ""
  list(
    type = progression$type,
    amount = progression$amount,
    message = paste(msg, collapse = ""),
    step = state$step,
    max_steps = config$max_steps
  )
}

one <- function() {
  seen <- list()
  handler <- make_progression_handler("rec", reporter = list(
    initiate = function(config, state, progression, ...) {
      seen[[length(seen) + 1L]] <<- record(config, state, progression)
    },
    update = function(config, state, progression, ...) {
      seen[[length(seen) + 1L]] <<- record(config, state, progression)
    }
  ), enable = TRUE, target = "file", interval = 0)
  total <- with_progress({
    p <- progressor(along = 1:5)
    s <- 0
    for (x in 1:5) {
      s <- s + x
      p(message = as.character(x))
    }
    s
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  list(sum = total, events = seen)
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
    '{"type":%s,"amount":%.17g,"message":%s,"step":%.17g,"max_steps":%.17g}',
    json_str(ev$type), ev$amount, json_str(ev$message), ev$step, ev$max_steps
  )
}, "")
cat(sprintf(
  '{"sum":%.17g,"events":[%s],"median_ms":%.17g}\n',
  value$sum,
  paste(events, collapse = ","),
  median(elapsed) * 1000
))
