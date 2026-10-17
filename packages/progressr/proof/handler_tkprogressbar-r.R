.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
library(tcltk)
options(progressr.enable = TRUE)

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
    ch
  }, character(1))
  paste0('"', paste(parts, collapse = ""), '"')
}

state <- function(steps, clear) {
  with_progress({
    p <- progressor(steps = 4, on_exit = FALSE)
    if (steps > 0) for (i in seq_len(steps)) p(message = paste0("m", i))
  }, handlers = handler_tkprogressbar(clear = clear, enable = TRUE),
     enable = TRUE, interval = 0, delay_terminal = FALSE,
     delay_stdout = FALSE, delay_conditions = character())
  wins <- as.character(tcl("winfo", "children", "."))
  wins <- wins[nzchar(wins)]
  if (length(wins) == 0) return(list(gone = TRUE))
  w <- wins[[length(wins)]]
  title <- paste(as.character(tcl("wm", "title", w)), collapse = " ")
  subs <- as.character(tcl("winfo", "children", w))
  label <- ""
  pct <- NA_real_
  for (s in subs) {
    cls <- tryCatch(as.character(tcl("winfo", "class", s))[[1]], error = function(e) "")
    if (identical(cls, "Label") && !nzchar(label)) {
      label <- paste(as.character(tcl(s, "cget", "-text")), collapse = " ")
    }
    if (identical(cls, "TProgressbar")) {
      var <- as.character(tcl(s, "cget", "-variable"))
      pct <- as.numeric(tcl("set", var))
    }
  }
  geom <- strsplit(as.character(tcl("wm", "geometry", w)), "+", fixed = TRUE)[[1]][[1]]
  tcl("destroy", w)
  list(gone = FALSE, title = title, label = label, percent = pct, geometry = geom)
}

one <- function() {
  bad <- tryCatch(
    handler_tkprogressbar(inputs = "x", enable = TRUE),
    error = function(e) conditionMessage(e)
  )
  list(
    bad_inputs = bad,
    none = state(0, FALSE),
    one = state(1, FALSE),
    four = state(4, FALSE),
    cleared = state(4, TRUE)
  )
}

snap <- function(item) {
  if (isTRUE(item$gone)) return('{"gone":true}')
  sprintf(
    '{"gone":false,"title":%s,"label":%s,"percent":%.17g,"geometry":%s}',
    json_str(item$title), json_str(item$label), item$percent, json_str(item$geometry)
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
  '{"bad_inputs":%s,"none":%s,"one":%s,"four":%s,"cleared":%s,"median_ms":%.17g}\n',
  json_str(value$bad_inputs), snap(value$none), snap(value$one),
  snap(value$four), snap(value$cleared), median(elapsed) * 1000
))
