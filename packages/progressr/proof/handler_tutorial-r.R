.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
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
    if (cp < 32 || cp == 127) return(sprintf("\\u%04x", cp))
    ch
  }, character(1))
  paste0('"', paste(parts, collapse = ""), '"')
}

one <- function() {
  handler <- handler_tutorial(spec = "cli", enable = TRUE)
  prefixed <- handler_tutorial(spec = "c", enable = TRUE)
  bad <- tryCatch(handler_tutorial(spec = "invalid"), error = function(e) conditionMessage(e))
  list(
    class = class(handler)[1],
    clear = environment(handler)$clear,
    target = environment(handler)$target,
    prefix = class(prefixed)[1],
    bad_spec = bad
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
  '{"class":%s,"clear":%s,"target":%s,"prefix":%s,"bad_spec":%s,"median_ms":%.17g}\n',
  json_str(value$class),
  if (isTRUE(value$clear)) "true" else "false",
  json_str(value$target),
  json_str(value$prefix),
  json_str(value$bad_spec),
  median(elapsed) * 1000
))
