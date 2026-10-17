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
json_num <- function(x) sprintf("%.17g", as.numeric(x))

one <- function() {
  handler <- handler_slowdown(duration = 0, enable = TRUE)
  total <- with_progress({
    p <- progressor(steps = 20, on_exit = FALSE)
    s <- 0
    for (i in 1:20) {
      p(message = "s")
      s <- s + i
    }
    s
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  list(
    intrusiveness = environment(handler)$intrusiveness,
    target = environment(handler)$target,
    result = total
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
  '{"intrusiveness":%s,"target":%s,"result":%s,"median_ms":%.17g}\n',
  json_num(value$intrusiveness), json_str(value$target), json_num(value$result),
  median(elapsed) * 1000
))
