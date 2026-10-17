suppressPackageStartupMessages(library(tseries))
options(warn = -1)

out_file <- "docs/output/get.hist.quote-r.txt"
instrument <- "^GSPC"
start <- "2020-01-02"
end <- "2020-03-31"

cell <- function(v) {
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    return(sprintf("%.17g", v))
  }
  as.character(v)
}

one <- function() {
  x <- get.hist.quote(instrument, start = start, end = end, quiet = TRUE)
  idx <- as.character(index(x))
  list(index = idx, colnames = colnames(x), values = as.numeric(coredata(x)),
       nrow = nrow(x))
}

is_network_error <- function(msg) grepl("429|HTTP|Could not resolve|timed out|download", msg)

result <- NULL
attempts <- 0
repeat {
  attempts <- attempts + 1
  result <- tryCatch(one(), error = function(e) e)
  if (!inherits(result, "error")) break
  if (!is_network_error(conditionMessage(result)) || attempts > 3) break
  Sys.sleep(30)
}

if (inherits(result, "error")) {
  writeLines(c(
    "status: blocked",
    paste0("instrument: ", instrument, " start: ", start, " end: ", end),
    paste0("attempts: ", attempts),
    paste0("error: ", conditionMessage(result))
  ), out_file)
  cat("blocked:", conditionMessage(result), "\n")
  quit(status = 2)
}

timed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  timed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}

lines <- c(
  "status: ok",
  paste0("nrow: ", result$nrow),
  paste0("colnames: ", paste(result$colnames, collapse = ",")),
  paste0("index: ", paste(result$index, collapse = ",")),
  paste0("values: ", paste(vapply(result$values, cell, ""), collapse = ",")),
  paste0("r_ms: ", sprintf("%.17g", median(timed)))
)
writeLines(lines, out_file)
cat(lines, sep = "\n")
