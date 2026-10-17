suppressPackageStartupMessages(library(cli))
options(cli.num_colors = 8, cli.unicode = TRUE)
emit <- function(x) {
  if (is.null(x)) {
    cat('NULL\n')
  } else if (is.logical(x) && length(x) == 1) {
    cat(if (isTRUE(x)) 'TRUE\n' else 'FALSE\n')
  } else if (is.numeric(x) && length(x) == 1 && !is.na(x)) {
    cat(sprintf('NUM %.17g\n', x))
  } else if (length(x) == 1 && is.na(x)) {
    cat('NA\n')
  } else {
    s <- enc2utf8(paste(ifelse(is.na(x), 'NA', as.character(x)), collapse = '|'))
    bytes <- as.integer(charToRaw(s))
    cat('STR ', paste(bytes, collapse = ','), '\n', sep = '')
  }
  invisible(NULL)
}
one <- function() { col_green("Hello") }
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
emit(value)
cat(sprintf('MS %.17g\n', median(elapsed) * 1000))
