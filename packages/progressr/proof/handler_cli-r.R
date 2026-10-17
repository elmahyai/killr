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
  ids <<- c(ids, if (length(val) == 1 && is.na(val)) "NA" else "id")
}, print = FALSE))
on.exit(untrace(cli::cli_progress_bar), add = TRUE)

formats <- function(type) {
  h <- handler_cli(type = type, enable = TRUE)
  env <- environment(environment(h)$reporter$initiate)
  backend <- parent.env(env)$backend_args
  list(format = backend$format, format_done = backend$format_done)
}

fmt_json <- function(pair) {
  sprintf('{"format":%s,"format_done":%s}', json_str(pair$format), json_str(pair$format_done))
}

run_cli <- function(steps, clear, type = "steps", show_after = 0, enable_after = NULL) {
  ids <<- character()
  args <- list(type = type, clear = clear, enable = TRUE, show_after = show_after)
  if (!is.null(enable_after)) args$enable_after <- enable_after
  handler <- do.call(handler_cli, args)
  err <- cap({
    with_progress({
      p <- progressor(steps = steps, on_exit = FALSE)
      if (steps > 0) for (i in seq_len(steps)) p(message = paste0("m", i))
    }, handlers = handler, enable = TRUE, interval = 0,
       delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  })
  list(called = length(ids) > 0, err = err)
}

run_json <- function(x) {
  sprintf('{"called":%s,"err":%s}', if (isTRUE(x$called)) "true" else "false", json_str(x$err))
}

one <- function() {
  custom_h <- handler_cli(type = "steps", format = "CUSTOM", enable = TRUE)
  env <- environment(environment(custom_h)$reporter$initiate)
  custom <- parent.env(env)$backend_args
  bad <- tryCatch(handler_cli(type = "nope"), error = function(e) conditionMessage(e))
  zero <- run_cli(0, FALSE, "default")
  shown <- run_cli(2, FALSE, "time", show_after = 1000)
  after <- run_cli(2, FALSE, "time", enable_after = 1000)
  sprintf(
    paste0(
      '{"default":%s,"steps":%s,"percent":%s,"time":%s,"prefix":%s,',
      '"custom_format":%s,"custom_done":%s,"bad_type":%s,',
      '"zero":%s,"show_called":%s,"after":%s'
    ),
    fmt_json(formats("default")),
    fmt_json(formats("steps")),
    fmt_json(formats("percent")),
    fmt_json(formats("time")),
    fmt_json(formats("st")),
    json_str(custom$format),
    json_str(custom$format_done),
    json_str(bad),
    run_json(zero),
    if (isTRUE(shown$called)) "true" else "false",
    run_json(after)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value)
cat(sprintf(',"median_ms":%.17g}\n', median(elapsed) * 1000))
