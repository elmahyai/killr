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
    ch
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}


one <- function() {
  events <- list()
  push <- function(progression) {
    events[[length(events) + 1L]] <<- list(type = progression$type, amount = as.numeric(progression$amount))
  }
  recorder <- make_progression_handler("record", reporter = list(
    initiate = function(config, state, progression, ...) push(progression),
    update = function(config, state, progression, ...) push(progression),
    finish = function(config, state, progression, ...) push(progression)
  ), enable = TRUE, intrusiveness = 1, interval = 0)
  value <- with_progress({
    bar <- progress_progressr()
    bar$init(3)
    bar$step()
    bar$step()
    bar$term()
    3
  }, handlers = recorder, enable = TRUE, interval = 0, delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  list(
    result = value,
    types = vapply(events, function(ev) ev$type, ""),
    amounts = vapply(events, function(ev) ev$amount, 0)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

types <- paste(vapply(value$types, json_str, ""), collapse = ",")
amounts <- paste(sprintf("%.17g", value$amounts), collapse = ",")
cat(sprintf('{"result":%.17g,"types":[%s],"amounts":[%s],"median_ms":%.17g}\n', value$result, types, amounts, median(elapsed) * 1000))
