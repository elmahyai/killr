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
  options(progressr.handlers = NULL)
  handler <- make_progression_handler("rec", reporter = list(
    update = function(config, state, progression, ...) NULL
  ), enable = TRUE, target = "file", interval = 0)
  second <- make_progression_handler("other", enable = TRUE, target = "file")
  handlers(rec = handler)
  current <- handlers()
  previous <- handlers(extra = second, append = TRUE)
  list(
    read_back = length(current),
    name = names(current)[[1]],
    previous = length(previous),
    after = length(handlers())
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
  '{"read_back":%.17g,"name":%s,"previous":%.17g,"after":%.17g,"median_ms":%.17g}\n',
  value$read_back,
  json_str(value$name),
  value$previous,
  value$after,
  median(elapsed) * 1000
))
