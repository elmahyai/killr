.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)
options(cli.num_colors = 1, width = 80)

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
  list(
    half = progressr:::pbcol(fraction = 0.5, msg = "Hi", width = 20),
    full = progressr:::pbcol(fraction = 1, msg = "", width = 12),
    long = progressr:::pbcol(fraction = 0.5, msg = paste(rep("x", 200), collapse = ""), width = 40)
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
  '{"half":%s,"full":%s,"long":%s,"median_ms":%.17g}\n',
  json_str(value$half), json_str(value$full), json_str(value$long),
  median(elapsed) * 1000
))
