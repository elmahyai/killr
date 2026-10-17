.libPaths(c("/home/ahmed/R/curl-8.1.0", path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(curl))
stopifnot(identical(as.character(packageVersion("curl")), "8.1.0"))
fmt <- function(v) {
  if (length(v) == 1L && is.na(v)) "NA" else as.character(v)
}
one <- function() {
  tbl <- curl_symbols("CURLAUTH")
  paste(
    paste(
      tbl$name,
      fmt(tbl$introduced),
      fmt(tbl$deprecated),
      fmt(tbl$removed),
      fmt(tbl$value),
      fmt(tbl$type),
      sep = "="
    ),
    collapse = "|"
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
