## Generic R side of the terminal-detection proof.
## Args: output path, setup code (may be ""), expression to time.
## The process is started with the same environment as the Python side,
## optionally inside a pseudo-terminal (see run_env_detect.py).

args <- commandArgs(trailingOnly = TRUE)
out_path <- args[1]
setup <- args[2]
expr_text <- args[3]

suppressPackageStartupMessages(library(crayon))

if (nzchar(setup)) eval(parse(text = setup), envir = globalenv())
expr <- parse(text = expr_text)[[1]]

hex_chr <- function(s) {
  paste(sprintf("%02x", as.integer(charToRaw(enc2utf8(s)))), collapse = "")
}

flatten <- function(x) {
  if (is.list(x)) unlist(lapply(x, flatten), use.names = FALSE) else x
}

## One untimed call.
value <- eval(expr, globalenv())

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  value <- eval(expr, globalenv())
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

value <- flatten(value)
lines <- c(
  sprintf("r_ms %.17g", median(elapsed) * 1000),
  sprintf("crayon_version %s", as.character(packageVersion("crayon")))
)
for (item in as.list(value)) {
  if (is.character(item)) {
    lines <- c(lines, paste("chr", hex_chr(item)))
  } else {
    lines <- c(lines, sprintf("num %.17g", as.numeric(item)))
  }
}
writeLines(lines, out_path)
