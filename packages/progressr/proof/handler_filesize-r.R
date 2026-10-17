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
json_bool <- function(x) if (isTRUE(x)) "true" else "false"
json_num <- function(x) sprintf("%.17g", as.numeric(x))

read_all <- function(path) {
  n <- file.info(path)$size
  if (is.na(n) || n == 0) return("")
  readChar(path, n, useBytes = TRUE)
}

one <- function() {
  bare <- handler_filesize(file = tempfile("fsdef"))
  fpath <- tempfile("fs")
  snaps <- with_progress({
    p <- progressor(steps = 4, on_exit = FALSE)
    init <- if (file.exists(fpath)) file.size(fpath) else -1
    p(message = "work")
    first <- read_all(fpath)
    p(amount = 0, message = "hold")
    zero <- read_all(fpath)
    p(message = "broke", amount = 1, type = "interrupt", class = "control_progression")
    interrupt <- read_all(fpath)
    p(message = "go")
    p(message = "go")
    p(message = "go")
    list(init = init, first = first, zero = zero, interrupt = interrupt)
  }, handlers = handler_filesize(file = fpath, enable = TRUE, clear = FALSE, intrusiveness = 0),
     enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  fclear <- tempfile("fsc")
  with_progress({
    p <- progressor(steps = 2, on_exit = FALSE)
    p(message = "x")
    p(message = "y")
  }, handlers = handler_filesize(file = fclear, enable = TRUE, clear = TRUE, intrusiveness = 0),
     enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  fzero <- tempfile("fsz")
  with_progress({
    p <- progressor(steps = 0, on_exit = FALSE)
  }, handlers = handler_filesize(file = fzero, enable = TRUE, clear = FALSE, intrusiveness = 0),
     enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  fdis <- tempfile("fsd")
  with_progress({
    p <- progressor(steps = 2, on_exit = FALSE)
    p(message = "x")
    p(message = "y")
  }, handlers = handler_filesize(file = fdis, enable = FALSE),
     enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  c(
    list(
      intrusiveness = environment(bare)$intrusiveness,
      target = environment(bare)$target,
      final = read_all(fpath),
      final_size = file.size(fpath),
      cleared = file.exists(fclear),
      zero_steps = read_all(fzero),
      zero_size = file.size(fzero),
      disabled = file.exists(fdis)
    ),
    snaps
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"intrusiveness":%s,"target":%s,"init":%s,"first":%s,"zero":%s,"interrupt":%s,"final":%s,"final_size":%s,"cleared":%s,"zero_steps":%s,"zero_size":%s,"disabled":%s,"median_ms":%.17g}\n',
  json_num(value$intrusiveness), json_str(value$target), json_num(value$init),
  json_str(value$first), json_str(value$zero), json_str(value$interrupt),
  json_str(value$final), json_num(value$final_size), json_bool(value$cleared),
  json_str(value$zero_steps), json_num(value$zero_size), json_bool(value$disabled),
  median(elapsed) * 1000
))
