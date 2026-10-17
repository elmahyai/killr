suppressPackageStartupMessages(library(clipr))

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

x <- c("Name's\tAge", "Alice\t30", "Bob\t25")
one <- function() read_clip_tbl(x)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
columns <- lapply(value, function(column) {
  if (is.character(column)) {
    paste0("[", paste(vapply(column, json_escape, ""), collapse = ","), "]")
  } else {
    paste0("[", paste(format(column, trim = TRUE, scientific = FALSE), collapse = ","), "]")
  }
})
cat(sprintf(
  "{\"columns\":{%s},\"row_names\":null,\"median_ms\":%.17g}\n",
  paste(paste0(json_escape(names(value)), ":", columns), collapse = ","),
  median(elapsed) * 1000
))
