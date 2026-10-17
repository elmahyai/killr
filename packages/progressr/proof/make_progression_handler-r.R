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
  steps <- numeric()
  messages <- character()
  handler <- make_progression_handler("rec", reporter = list(
    update = function(config, state, progression, ...) {
      steps <<- c(steps, state$step)
      messages <<- c(messages, state$message)
    }
  ), enable = TRUE, target = "file", interval = 0)
  withCallingHandlers({
    signalCondition(progression(
      type = "initiate", steps = 4, auto_finish = TRUE,
      progressor_uuid = "p", progression_index = 1L
    ))
    signalCondition(progression(
      type = "update", amount = 1, message = "a",
      progressor_uuid = "p", progression_index = 2L
    ))
    signalCondition(progression(
      type = "update", amount = 1, message = "b",
      progressor_uuid = "p", progression_index = 3L
    ))
    signalCondition(progression(
      type = "update", amount = 1, message = "c",
      progressor_uuid = "p", progression_index = 4L
    ))
    signalCondition(progression(
      type = "update", amount = 1, message = "d",
      progressor_uuid = "p", progression_index = 5L
    ))
  }, progression = handler)
  list(steps = steps, messages = messages)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
steps <- paste(sprintf("%.17g", value$steps), collapse = ",")
messages <- paste(vapply(value$messages, json_str, ""), collapse = ",")
cat(sprintf(
  '{"steps":[%s],"messages":[%s],"median_ms":%.17g}\n',
  steps, messages, median(elapsed) * 1000
))
