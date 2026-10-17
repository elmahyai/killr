suppressPackageStartupMessages(library(cli))
options(cli.num_colors = 8, cli.unicode = TRUE, width = 80)
emit <- function(x) {
  if (is.null(x)) {
    cat('NULL\n')
  } else if (is.logical(x) && length(x) == 1 && !is.na(x)) {
    cat(if (isTRUE(x)) 'TRUE\n' else 'FALSE\n')
  } else if (is.numeric(x) && length(x) == 1 && !is.na(x)) {
    cat(sprintf('NUM %.17g\n', x))
  } else {
    s <- enc2utf8(paste(ifelse(is.na(x), 'NA', as.character(x)), collapse = '|'))
    cat('STR ', paste(as.integer(charToRaw(s)), collapse = ','), '\n', sep = '')
  }
  invisible(NULL)
}
one <- function() { paste(ansi_strwrap("one two three four", width=10), collapse="|") }
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
emit(value)
cat(sprintf('MS %.17g\n', median(elapsed) * 1000))
