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
json_num <- function(x) sprintf("%.17g", as.numeric(x))
json_bool <- function(x) if (isTRUE(x)) "true" else "false"

parse_line <- function(line) {
  suffix <- grepl(" [progressor=", line, fixed = TRUE)
  line <- sub(" \\[progressor=.*$", "", line)
  pat <- "^\\[.*\\] \\([0-9.]+s => \\+[+-]?[0-9.]+s\\) ([^:]+): ([0-9.]+)/([0-9.]+) \\(([+-][^)]*)\\) '(.*)' \\{clear=([^,]*), enabled=([^,]*), status=(.*)\\}$"
  matched <- regexec(pat, line, perl = TRUE)
  parts <- regmatches(line, matched)[[1]]
  if (length(parts) == 0) stop("unparsed: ", line)
  list(
    type = parts[[2]],
    step = as.numeric(parts[[3]]),
    max_steps = as.numeric(parts[[4]]),
    delta = as.numeric(parts[[5]]),
    message = parts[[6]],
    clear = parts[[7]],
    enabled = parts[[8]],
    status = parts[[9]],
    uuid_suffix = suffix
  )
}

capture_debug <- function(handler, expr) {
  path <- tempfile("dbg")
  con <- file(path, open = "wt")
  sink(con, type = "message")
  force(expr)
  sink(type = "message")
  close(con)
  lines <- readLines(path, warn = FALSE)
  lapply(lines, parse_line)
}

one <- function() {
  plain <- capture_debug(handler_debug(enable = TRUE, uuid = FALSE), with_progress({
    p <- progressor(steps = 4, on_exit = FALSE)
    p(message = "one")
    p(message = "two", amount = 0, class = "sticky")
    p(message = "halt", amount = 0, type = "interrupt", class = "control_progression")
    p(message = "three")
    p(message = "four")
  }, handlers = handler_debug(enable = TRUE, uuid = FALSE), enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character()))
  marked <- capture_debug(handler_debug(enable = TRUE, uuid = TRUE), with_progress({
    p <- progressor(steps = 1, on_exit = FALSE)
    p(message = "z")
  }, handlers = handler_debug(enable = TRUE, uuid = TRUE), enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character()))
  list(events = plain, uuid_events = marked)
}

event_json <- function(ev) {
  paste0(
    '{"type":', json_str(ev$type),
    ',"step":', json_num(ev$step),
    ',"max_steps":', json_num(ev$max_steps),
    ',"delta":', json_num(ev$delta),
    ',"message":', json_str(ev$message),
    ',"clear":', json_str(ev$clear),
    ',"enabled":', json_str(ev$enabled),
    ',"status":', json_str(ev$status), "}"
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
uuid_suffix <- all(vapply(value$uuid_events, function(ev) isTRUE(ev$uuid_suffix), TRUE))
cat(sprintf(
  '{"events":[%s],"uuid_events":[%s],"uuid_suffix":%s,"median_ms":%.17g}\n',
  paste(vapply(value$events, event_json, ""), collapse = ","),
  paste(vapply(value$uuid_events, event_json, ""), collapse = ","),
  json_bool(uuid_suffix),
  median(elapsed) * 1000
))
